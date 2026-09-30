//! Rewrites Painter layer payloads so an sRGB Photoshop document reproduces
//! Painter's linear-space look (design.md §4, analysis.md §6.2-6.3).
//!
//! The caller passes a program: one line per stack step, bottom to top, with
//! raw pixel files for inputs and outputs. Every operation is per pixel, so
//! rows are processed in strips across threads and no image is ever held
//! whole; a 4K stack of dozens of layers would not fit in memory otherwise.

use std::fs::{File, OpenOptions};
use std::os::windows::fs::FileExt;
use std::sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering};
use std::sync::Mutex;

const EPS: f32 = 1e-6;
// Rows per work item. Each thread holds every layer's rows at once, so this
// stays small: 40 layers of an 8K PSD would otherwise need gigabytes.
const STRIP_ROWS: usize = 4;

#[derive(Clone, Copy, PartialEq)]
enum Mode {
    Normal, Multiply, Screen, Overlay, SoftLight, HardLight, Darken, Lighten,
    LinearDodge, LinearBurn, ColorBurn, ColorDodge, VividLight, LinearLight,
    PinLight, Difference, Exclusion, Subtract, Divide, InverseDivide,
    InverseSubtract, Tint, Saturation, Color, Value,
}

impl Mode {
    fn parse(name: &str) -> Result<Mode, String> {
        Ok(match name {
            "Normal" => Mode::Normal,
            "Multiply" => Mode::Multiply,
            "Screen" => Mode::Screen,
            "Overlay" => Mode::Overlay,
            "SoftLight" => Mode::SoftLight,
            "HardLight" => Mode::HardLight,
            "Darken" => Mode::Darken,
            "Lighten" => Mode::Lighten,
            "LinearDodge" => Mode::LinearDodge,
            "LinearBurn" => Mode::LinearBurn,
            "ColorBurn" => Mode::ColorBurn,
            "ColorDodge" => Mode::ColorDodge,
            "VividLight" => Mode::VividLight,
            // Measured identical to LinearLight (analysis.md §6.2).
            "LinearLight" | "SignedAddition" => Mode::LinearLight,
            "PinLight" => Mode::PinLight,
            "Difference" => Mode::Difference,
            "Exclusion" => Mode::Exclusion,
            "Subtract" => Mode::Subtract,
            "Divide" => Mode::Divide,
            "InverseDivide" => Mode::InverseDivide,
            "InverseSubtract" => Mode::InverseSubtract,
            "Tint" => Mode::Tint,
            "Saturation" => Mode::Saturation,
            "Color" => Mode::Color,
            "Value" => Mode::Value,
            other => return Err(format!("unknown blend mode {other}")),
        })
    }
}

#[derive(Clone, Copy, PartialEq)]
enum Emit {
    /// Normal-mode pixels solved against the Photoshop backdrop, raising
    /// coverage when sRGB mixing needs it (Match Painter look).
    Solve,
    /// Multiply/Divide color rewrite from coverage; backdrop independent.
    Multiply,
    Divide,
    /// Color-only solve at the original coverage (Keep blend modes).
    Color,
    /// Contributes to the composite; its payload is left as it is.
    None,
}

struct Raw {
    path: String,
    depth: usize, // 8 or 16
    channels: usize, // 1 or 4
    stride: usize,
}

struct Leaf {
    mode: Mode,
    opacity: f32,
    visible: bool,
    content: Raw,
    mask: Option<Raw>,
    emit: Emit,
    out_content: Option<Raw>,
    out_mask: Option<Raw>,
    /// Coverage of pass-through ancestors folded into this leaf's pixels.
    fold_ancestors: bool,
}

enum Op {
    Begin { pass: bool, mode: Mode, opacity: f32, mask: Option<Raw> },
    End,
    Leaf(Box<Leaf>),
}

struct Program {
    width: usize,
    height: usize,
    srgb: bool,
    ops: Vec<Op>,
}

fn parse_raw(path: &str, depth: &str, channels: usize, width: usize, stride: &str) -> Result<Option<Raw>, String> {
    if path == "-" {
        return Ok(None);
    }
    let depth: usize = depth.parse().map_err(|_| format!("bad depth {depth}"))?;
    if depth != 8 && depth != 16 {
        return Err(format!("unsupported depth {depth}"));
    }
    let tight = width * channels * depth / 8;
    let stride = if stride == "-" { tight } else { stride.parse().map_err(|_| format!("bad stride {stride}"))? };
    if stride < tight {
        return Err(format!("stride {stride} is shorter than a row"));
    }
    Ok(Some(Raw { path: path.to_string(), depth, channels, stride }))
}

fn parse_f32(value: &str) -> Result<f32, String> {
    value.parse().map_err(|_| format!("bad number {value}"))
}

fn parse_program(text: &str) -> Result<Program, String> {
    let mut lines = text.lines().filter(|line| !line.is_empty());
    let header: Vec<&str> = lines.next().ok_or("empty program")?.split('\t').collect();
    if header.len() != 4 || header[0] != "P" {
        return Err("bad header".into());
    }
    let width: usize = header[1].parse().map_err(|_| "bad width")?;
    let height: usize = header[2].parse().map_err(|_| "bad height")?;
    let srgb = match header[3] { "srgb" => true, "raw" => false, other => return Err(format!("bad transfer {other}")) };
    let mut ops = Vec::new();
    let mut depth = 0i32;
    for line in lines {
        let f: Vec<&str> = line.split('\t').collect();
        match f[0] {
            "B" if f.len() == 7 => {
                depth += 1;
                ops.push(Op::Begin {
                    pass: f[1] == "1",
                    mode: Mode::parse(f[2])?,
                    opacity: parse_f32(f[3])?,
                    mask: parse_raw(f[4], f[5], 1, width, f[6])?,
                });
            }
            "E" => {
                depth -= 1;
                if depth < 0 {
                    return Err("unbalanced group end".into());
                }
                ops.push(Op::End);
            }
            // L mode opacity visible emit fold content depth stride mask depth stride out_content out_mask
            "L" if f.len() == 14 => {
                let emit = match f[4] {
                    "solve" => Emit::Solve,
                    "multiply" => Emit::Multiply,
                    "divide" => Emit::Divide,
                    "color" => Emit::Color,
                    "none" => Emit::None,
                    other => return Err(format!("bad emit {other}")),
                };
                let content = parse_raw(f[6], f[7], 4, width, f[8])?.ok_or("leaf without content")?;
                let mask = parse_raw(f[9], f[10], 1, width, f[11])?;
                let out_content = parse_raw(f[12], &content.depth.to_string(), 4, width, "-")?;
                let out_mask = match (&mask, f[13]) {
                    (_, "-") => None,
                    (Some(m), path) => parse_raw(path, &m.depth.to_string(), 1, width, "-")?,
                    (None, _) => return Err("mask output without mask input".into()),
                };
                if emit != Emit::None && out_content.is_none() {
                    return Err("emitting leaf without output".into());
                }
                ops.push(Op::Leaf(Box::new(Leaf {
                    mode: Mode::parse(f[1])?,
                    opacity: parse_f32(f[2])?,
                    visible: f[3] == "1",
                    emit,
                    fold_ancestors: f[5] == "1",
                    content,
                    mask,
                    out_content,
                    out_mask,
                })));
            }
            _ => return Err(format!("bad program line: {line}")),
        }
    }
    if depth != 0 {
        return Err("unbalanced group".into());
    }
    Ok(Program { width, height, srgb, ops })
}

// ---------------------------------------------------------------- color math

fn lin(x: f32) -> f32 {
    if x <= 0.04045 { x / 12.92 } else { ((x + 0.055) / 1.055).powf(2.4) }
}

fn enc(x: f32) -> f32 {
    let x = x.clamp(0.0, 1.0);
    if x <= 0.003_130_8 { 12.92 * x } else { 1.055 * x.powf(1.0 / 2.4) - 0.055 }
}

/// sRGB encoding continued past 1, for the Divide rewrite's gain factor.
fn enc_gain(x: f32) -> f32 {
    if x <= 1.0 { enc(x) } else { 1.055 * x.powf(1.0 / 2.4) - 0.055 }
}

fn clamp01(x: f32) -> f32 {
    x.clamp(0.0, 1.0)
}

fn channel_blend(mode: Mode, b: f32, c: f32) -> f32 {
    let v = match mode {
        Mode::Normal => c,
        Mode::Multiply => b * c,
        Mode::Screen => 1.0 - (1.0 - b) * (1.0 - c),
        Mode::Overlay => if b < 0.5 { 2.0 * b * c } else { 1.0 - 2.0 * (1.0 - b) * (1.0 - c) },
        Mode::HardLight => if c < 0.5 { 2.0 * b * c } else { 1.0 - 2.0 * (1.0 - b) * (1.0 - c) },
        Mode::SoftLight => {
            if c <= 0.5 { b - (1.0 - 2.0 * c) * b * (1.0 - b) } else { b + (2.0 * c - 1.0) * (b.max(0.0).sqrt() - b) }
        }
        Mode::Darken => b.min(c),
        Mode::Lighten => b.max(c),
        Mode::LinearDodge => b + c,
        Mode::LinearBurn => b + c - 1.0,
        Mode::ColorBurn => 1.0 - (1.0 - b) / c.max(EPS),
        Mode::ColorDodge => b / (1.0 - c).max(EPS),
        Mode::VividLight => {
            if c < 0.5 { 1.0 - (1.0 - b) / (2.0 * c).max(EPS) } else { b / (2.0 * (1.0 - c)).max(EPS) }
        }
        Mode::LinearLight => b + 2.0 * c - 1.0,
        Mode::PinLight => if c < 0.5 { b.min(2.0 * c) } else { b.max(2.0 * c - 1.0) },
        Mode::Difference => (b - c).abs(),
        Mode::Exclusion => b + c - 2.0 * b * c,
        Mode::Subtract => b - c,
        Mode::Divide => b / c.max(EPS),
        Mode::InverseDivide => c / b.max(EPS),
        Mode::InverseSubtract => c - b,
        Mode::Tint | Mode::Saturation | Mode::Color | Mode::Value => unreachable!(),
    };
    clamp01(v)
}

fn rgb_to_hsv(c: [f32; 3]) -> [f32; 3] {
    let max = c[0].max(c[1]).max(c[2]);
    let min = c[0].min(c[1]).min(c[2]);
    let d = max - min;
    let s = if max > 0.0 { d / max.max(EPS) } else { 0.0 };
    let h = if d <= 0.0 {
        0.0
    } else if max == c[0] {
        ((c[1] - c[2]) / d).rem_euclid(6.0) / 6.0
    } else if max == c[1] {
        ((c[2] - c[0]) / d + 2.0) / 6.0
    } else {
        ((c[0] - c[1]) / d + 4.0) / 6.0
    };
    [h, s, max]
}

fn hsv_to_rgb(hsv: [f32; 3]) -> [f32; 3] {
    let h = hsv[0] * 6.0;
    let (s, v) = (hsv[1], hsv[2]);
    let i = h.floor().rem_euclid(6.0) as i32;
    let f = h - h.floor();
    let p = v * (1.0 - s);
    let q = v * (1.0 - s * f);
    let t = v * (1.0 - s * (1.0 - f));
    match i {
        0 => [v, t, p],
        1 => [q, v, p],
        2 => [p, v, t],
        3 => [p, q, v],
        4 => [t, p, v],
        _ => [v, p, q],
    }
}

fn blend(mode: Mode, b: [f32; 3], c: [f32; 3]) -> [f32; 3] {
    match mode {
        Mode::Tint | Mode::Saturation | Mode::Color | Mode::Value => {
            let mut out = rgb_to_hsv(b);
            let top = rgb_to_hsv(c);
            match mode {
                Mode::Tint => out[0] = top[0],
                Mode::Saturation => out[1] = top[1],
                Mode::Color => { out[0] = top[0]; out[1] = top[1]; }
                _ => out[2] = top[2],
            }
            // Painter doubles the value in every HSV mode; measured at a
            // constant 2.000 ratio (analysis.md §6.2).
            out[2] *= 2.0;
            let rgb = hsv_to_rgb(out);
            [clamp01(rgb[0]), clamp01(rgb[1]), clamp01(rgb[2])]
        }
        _ => [channel_blend(mode, b[0], c[0]), channel_blend(mode, b[1], c[1]), channel_blend(mode, b[2], c[2])],
    }
}

/// Premultiplied color plus alpha.
#[derive(Clone, Copy)]
struct Px {
    rgb: [f32; 3],
    a: f32,
}

const CLEAR: Px = Px { rgb: [0.0; 3], a: 0.0 };

fn straight(p: Px) -> [f32; 3] {
    if p.a > EPS {
        [p.rgb[0] / p.a, p.rgb[1] / p.a, p.rgb[2] / p.a]
    } else {
        [0.0; 3]
    }
}

/// Separable compositing with backdrop alpha: where the backdrop is empty the
/// source shows its own color, which is how both Painter and Photoshop treat
/// a blend mode over transparency.
fn over(dst: Px, src_color: [f32; 3], sa: f32, mode: Mode) -> Px {
    if sa <= 0.0 {
        return dst;
    }
    let cb = straight(dst);
    let mixed = blend(mode, cb, src_color);
    let mut rgb = [0.0; 3];
    for i in 0..3 {
        let mix = (1.0 - dst.a) * src_color[i] + dst.a * mixed[i];
        rgb[i] = (1.0 - sa) * dst.rgb[i] + sa * mix;
    }
    Px { rgb, a: sa + dst.a * (1.0 - sa) }
}

fn lerp_px(from: Px, to: Px, t: f32) -> Px {
    let mut rgb = [0.0; 3];
    for i in 0..3 {
        rgb[i] = from.rgb[i] + (to.rgb[i] - from.rgb[i]) * t;
    }
    Px { rgb, a: from.a + (to.a - from.a) * t }
}

/// Photoshop's sRGB blend formula for the modes a rewrite keeps.
fn ps_channel(mode: Mode, b: f32, c: f32) -> f32 {
    match mode {
        Mode::Multiply => b * c,
        Mode::Divide => clamp01(b / c.max(EPS)),
        _ => c,
    }
}

fn ps_over(dst: Px, color: [f32; 3], a: f32, mode: Mode) -> Px {
    if a <= 0.0 {
        return dst;
    }
    let cb = straight(dst);
    let mut rgb = [0.0; 3];
    for i in 0..3 {
        let mix = (1.0 - dst.a) * color[i] + dst.a * ps_channel(mode, cb[i], color[i]);
        rgb[i] = (1.0 - a) * dst.rgb[i] + a * mix;
    }
    Px { rgb, a: a + dst.a * (1.0 - a) }
}

// ---------------------------------------------------------------- pixel I/O

struct Strip {
    data: Vec<f32>,
}

fn read_strip(raw: &Raw, file: &File, width: usize, row0: usize, rows: usize) -> Result<Strip, String> {
    let bytes_per_sample = raw.depth / 8;
    let tight = width * raw.channels * bytes_per_sample;
    let mut bytes = vec![0u8; tight];
    let mut data = Vec::with_capacity(width * raw.channels * rows);
    for row in row0..row0 + rows {
        file.seek_read(&mut bytes, (row * raw.stride) as u64)
            .map_err(|e| format!("{}: {e}", raw.path))
            .and_then(|n| if n == tight { Ok(()) } else { Err(format!("{}: short read", raw.path)) })?;
        if bytes_per_sample == 1 {
            data.extend(bytes.iter().map(|&v| v as f32 / 255.0));
        } else {
            data.extend(bytes.chunks_exact(2).map(|v| u16::from_le_bytes([v[0], v[1]]) as f32 / 65535.0));
        }
    }
    Ok(Strip { data })
}

fn quantize(value: f32, depth: usize) -> f32 {
    let scale = if depth == 8 { 255.0 } else { 65535.0 };
    (clamp01(value) * scale).round() / scale
}

fn write_rows(raw: &Raw, file: &File, width: usize, row0: usize, values: &[f32]) -> Result<(), String> {
    let row_bytes = width * raw.channels * raw.depth / 8;
    let mut bytes = Vec::with_capacity(values.len() * raw.depth / 8);
    if raw.depth == 8 {
        bytes.extend(values.iter().map(|&v| (clamp01(v) * 255.0).round() as u8));
    } else {
        for &v in values {
            bytes.extend_from_slice(&((clamp01(v) * 65535.0).round() as u16).to_le_bytes());
        }
    }
    file.seek_write(&bytes, (row0 * row_bytes) as u64).map_err(|e| format!("{}: {e}", raw.path))?;
    Ok(())
}

// ---------------------------------------------------------------- evaluation

struct Context {
    pass: bool,
    mode: Mode,
    cov: f32,
    /// Painter state inside this group (the parent's state when it began,
    /// for a pass-through group).
    state: Px,
}

/// Painter's composite if the stack ended here: open groups folded outward.
fn close_all(contexts: &[Context]) -> Px {
    let mut current = contexts[contexts.len() - 1].state;
    for i in (1..contexts.len()).rev() {
        let group = &contexts[i];
        let parent = contexts[i - 1].state;
        current = fold(parent, current, group);
    }
    current
}

fn fold(parent: Px, inner: Px, group: &Context) -> Px {
    if group.pass {
        lerp_px(parent, inner, group.cov)
    } else {
        let a = inner.a * group.cov;
        over(parent, straight(inner), a, group.mode)
    }
}

struct Transfer {
    srgb: bool,
}

impl Transfer {
    fn to_linear(&self, c: [f32; 3]) -> [f32; 3] {
        if self.srgb { [lin(c[0]), lin(c[1]), lin(c[2])] } else { c }
    }
    fn to_output(&self, c: [f32; 3]) -> [f32; 3] {
        if self.srgb { [enc(c[0]), enc(c[1]), enc(c[2])] } else { [clamp01(c[0]), clamp01(c[1]), clamp01(c[2])] }
    }
    fn encode(&self, x: f32) -> f32 {
        if self.srgb { enc(x) } else { clamp01(x) }
    }
    fn gain(&self, x: f32) -> f32 {
        if self.srgb { enc_gain(x) } else { x }
    }
}

/// The encoded straight color and alpha of a linear premultiplied pixel.
fn encoded(p: Px, t: &Transfer) -> ([f32; 3], f32) {
    (t.to_output(straight(p)), p.a)
}

struct LeafOutput {
    content: Vec<f32>,
    mask: Option<Vec<f32>>,
}

fn run_strip(program: &Program, files: &[Option<(File, Option<File>, Option<File>, Option<File>)>],
             group_masks: &[Option<File>], row0: usize, rows: usize, stats: &Stats) -> Result<(), String> {
    let width = program.width;
    let transfer = Transfer { srgb: program.srgb };
    // Load inputs for this strip.
    let mut leaf_inputs: Vec<Option<(Strip, Option<Strip>)>> = Vec::with_capacity(program.ops.len());
    let mut group_inputs: Vec<Option<Strip>> = Vec::with_capacity(program.ops.len());
    let mut outputs: Vec<Option<LeafOutput>> = Vec::with_capacity(program.ops.len());
    for (index, op) in program.ops.iter().enumerate() {
        match op {
            Op::Leaf(leaf) => {
                let (content_file, mask_file, _, _) = files[index].as_ref().unwrap();
                let content = read_strip(&leaf.content, content_file, width, row0, rows)?;
                let mask = match (&leaf.mask, mask_file) {
                    (Some(raw), Some(file)) => Some(read_strip(raw, file, width, row0, rows)?),
                    _ => None,
                };
                leaf_inputs.push(Some((content, mask)));
                group_inputs.push(None);
                outputs.push(leaf.out_content.as_ref().map(|_| LeafOutput {
                    content: vec![0.0; width * rows * 4],
                    mask: leaf.out_mask.as_ref().map(|_| vec![0.0; width * rows]),
                }));
            }
            Op::Begin { mask: Some(raw), .. } => {
                group_inputs.push(Some(read_strip(raw, group_masks[index].as_ref().unwrap(), width, row0, rows)?));
                leaf_inputs.push(None);
                outputs.push(None);
            }
            _ => {
                group_inputs.push(None);
                leaf_inputs.push(None);
                outputs.push(None);
            }
        }
    }

    let mut contexts: Vec<Context> = Vec::new();
    for pixel in 0..width * rows {
        contexts.clear();
        contexts.push(Context { pass: true, mode: Mode::Normal, cov: 1.0, state: CLEAR });
        // Photoshop's running composite, encoded premultiplied. Match Painter
        // look turns every folder into Pass Through, so one buffer holds it.
        let mut ps = CLEAR;
        for (index, op) in program.ops.iter().enumerate() {
            match op {
                Op::Begin { pass, mode, opacity, .. } => {
                    let mut cov = *opacity;
                    if let Some(mask) = &group_inputs[index] {
                        cov *= mask.data[pixel];
                    }
                    let parent = contexts[contexts.len() - 1].state;
                    contexts.push(Context {
                        pass: *pass,
                        mode: *mode,
                        cov,
                        state: if *pass { parent } else { CLEAR },
                    });
                }
                Op::End => {
                    let group = contexts.pop().unwrap();
                    let parent = contexts.len() - 1;
                    contexts[parent].state = fold(contexts[parent].state, group.state, &group);
                }
                Op::Leaf(leaf) => {
                    let (content, mask) = leaf_inputs[index].as_ref().unwrap();
                    let c = &content.data[pixel * 4..pixel * 4 + 4];
                    let pixel_alpha = c[3];
                    let mask_value = mask.as_ref().map(|m| m.data[pixel]);
                    let own_cov = pixel_alpha * leaf.opacity * mask_value.unwrap_or(1.0);
                    let ancestors: f32 = contexts[1..].iter().map(|g| g.cov).product();
                    let color = transfer.to_linear([c[0], c[1], c[2]]);

                    let before = if leaf.emit == Emit::Color { Some(close_all(&contexts)) } else { None };
                    if leaf.visible {
                        let top = contexts.len() - 1;
                        contexts[top].state = over(contexts[top].state, color, own_cov, leaf.mode);
                    }
                    if leaf.emit == Emit::None {
                        continue;
                    }
                    let target = close_all(&contexts);
                    let (tc, ta) = encoded(target, &transfer);
                    let out = outputs[index].as_mut().unwrap();
                    let (rgb, alpha, new_mask, ps_mode) = match leaf.emit {
                        Emit::Solve => {
                            let (bc, ba) = (straight(ps), ps.a);
                            let floor = own_cov * ancestors;
                            let coverage = if ba >= 1.0 - EPS {
                                let mut need: f32 = 0.0;
                                for i in 0..3 {
                                    let d = tc[i] - bc[i];
                                    let n = if d > 0.0 { d / (1.0 - bc[i]).max(EPS) } else if d < 0.0 { -d / bc[i].max(EPS) } else { 0.0 };
                                    need = need.max(n);
                                }
                                clamp01(floor.max(need))
                            } else {
                                clamp01((ta - ba) / (1.0 - ba))
                            };
                            let mut rgb = [0.0; 3];
                            if coverage > EPS {
                                let mut clipped_here = false;
                                for i in 0..3 {
                                    let v = (ta * tc[i] - (1.0 - coverage) * ba * bc[i]) / coverage;
                                    if !(-1e-3..=1.0 + 1e-3).contains(&v) {
                                        clipped_here = true;
                                    }
                                    rgb[i] = clamp01(v);
                                }
                                if clipped_here {
                                    stats.clipped[index].fetch_add(1, Ordering::Relaxed);
                                }
                            }
                            // Extra coverage goes into pixel alpha first; the
                            // mask changes only where pixel alpha is full.
                            let (alpha, new_mask) = match mask_value {
                                Some(m) if coverage <= m => (if m > EPS { coverage / m } else { 0.0 }, Some(m)),
                                Some(_) => (1.0, Some(coverage)),
                                None => (coverage, None),
                            };
                            (rgb, alpha, new_mask, Mode::Normal)
                        }
                        Emit::Multiply | Emit::Divide => {
                            // Photoshop reaches the same total coverage either
                            // way: Match Painter look folds opacity and Pass
                            // Through folders into pixel alpha, Keep blend
                            // modes leaves them on the layer and folders.
                            let a = own_cov * ancestors;
                            let pixel_out = if leaf.fold_ancestors { pixel_alpha * leaf.opacity * ancestors } else { pixel_alpha };
                            let mut rgb = [c[0], c[1], c[2]];
                            if a > EPS {
                                for i in 0..3 {
                                    rgb[i] = if leaf.emit == Emit::Multiply {
                                        let m = 1.0 - a + a * color[i];
                                        clamp01(1.0 - (1.0 - transfer.encode(m)) / a)
                                    } else {
                                        let k = 1.0 - a + a / color[i].max(EPS);
                                        clamp01(a / (transfer.gain(k) - 1.0 + a).max(EPS))
                                    };
                                }
                            }
                            (rgb, pixel_out, mask_value, if leaf.emit == Emit::Multiply { Mode::Multiply } else { Mode::Divide })
                        }
                        Emit::Color => {
                            let (bc, ba) = encoded(before.unwrap(), &transfer);
                            let a = own_cov * ancestors;
                            let mut rgb = [c[0], c[1], c[2]];
                            if a > EPS {
                                for i in 0..3 {
                                    rgb[i] = clamp01((ta * tc[i] - (1.0 - a) * ba * bc[i]) / a);
                                }
                            }
                            (rgb, pixel_alpha, mask_value, Mode::Normal)
                        }
                        Emit::None => unreachable!(),
                    };
                    let depth = leaf.content.depth;
                    let rgb_q = [quantize(rgb[0], depth), quantize(rgb[1], depth), quantize(rgb[2], depth)];
                    let alpha_q = quantize(alpha, depth);
                    out.content[pixel * 4..pixel * 4 + 4].copy_from_slice(&[rgb_q[0], rgb_q[1], rgb_q[2], alpha_q]);
                    let mask_q = new_mask.map(|m| quantize(m, leaf.mask.as_ref().map_or(depth, |r| r.depth)));
                    let step = 0.5 / if depth == 8 { 255.0 } else { 65535.0 };
                    let content_changed = (0..3).any(|i| (rgb_q[i] - c[i]).abs() > step) || (alpha_q - c[3]).abs() > step;
                    let mask_changed = match (mask_q, mask_value) {
                        (Some(new), Some(old)) => (new - old).abs() > step,
                        _ => false,
                    };
                    if content_changed || mask_changed {
                        stats.changed[index].fetch_add(1, Ordering::Relaxed);
                    }
                    if let (Some(buffer), Some(m)) = (out.mask.as_mut(), mask_q) {
                        buffer[pixel] = m;
                    }
                    if leaf.emit != Emit::Color {
                        // Track what Photoshop will composite, from the
                        // quantized pixels it will actually read.
                        let coverage = alpha_q * mask_q.unwrap_or(1.0);
                        ps = ps_over(ps, rgb_q, coverage, ps_mode);
                    }
                }
            }
        }
    }

    for (index, op) in program.ops.iter().enumerate() {
        if let (Op::Leaf(leaf), Some(out)) = (op, outputs[index].as_ref()) {
            let (_, _, out_content, out_mask) = files[index].as_ref().unwrap();
            write_rows(leaf.out_content.as_ref().unwrap(), out_content.as_ref().unwrap(), width, row0, &out.content)?;
            if let (Some(raw), Some(file), Some(values)) = (leaf.out_mask.as_ref(), out_mask.as_ref(), out.mask.as_ref()) {
                write_rows(raw, file, width, row0, values)?;
            }
        }
    }
    Ok(())
}

struct Stats {
    /// Pixels the solve had to clip, so they do not match Painter exactly.
    clipped: Vec<AtomicU64>,
    /// Pixels whose output differs from the payload, so an unchanged
    /// payload need not be re-encoded.
    changed: Vec<AtomicU64>,
}

fn run(program: &Program, threads: usize, stats: &Stats) -> Result<(), String> {
    let open_input = |raw: &Raw| File::open(&raw.path).map_err(|e| format!("{}: {e}", raw.path));
    let open_output = |raw: &Raw| {
        OpenOptions::new().write(true).open(&raw.path).map_err(|e| format!("{}: {e}", raw.path))
    };
    // Size every output once up front, so strips can be written in any order.
    for op in &program.ops {
        if let Op::Leaf(leaf) = op {
            for raw in [leaf.out_content.as_ref(), leaf.out_mask.as_ref()].into_iter().flatten() {
                let file = OpenOptions::new().write(true).create(true).truncate(true).open(&raw.path)
                    .map_err(|e| format!("{}: {e}", raw.path))?;
                let len = program.width * program.height * raw.channels * raw.depth / 8;
                file.set_len(len as u64).map_err(|e| format!("{}: {e}", raw.path))?;
            }
        }
    }
    let next = AtomicUsize::new(0);
    let failed = AtomicBool::new(false);
    let error: Mutex<Option<String>> = Mutex::new(None);
    std::thread::scope(|scope| {
        for _ in 0..threads {
            scope.spawn(|| {
                let opened = (|| -> Result<_, String> {
                    let mut files = Vec::new();
                    let mut group_masks = Vec::new();
                    for op in &program.ops {
                        match op {
                            Op::Leaf(leaf) => {
                                files.push(Some((
                                    open_input(&leaf.content)?,
                                    leaf.mask.as_ref().map(open_input).transpose()?,
                                    leaf.out_content.as_ref().map(open_output).transpose()?,
                                    leaf.out_mask.as_ref().map(open_output).transpose()?,
                                )));
                                group_masks.push(None);
                            }
                            Op::Begin { mask, .. } => {
                                files.push(None);
                                group_masks.push(mask.as_ref().map(open_input).transpose()?);
                            }
                            Op::End => {
                                files.push(None);
                                group_masks.push(None);
                            }
                        }
                    }
                    Ok((files, group_masks))
                })();
                let (files, group_masks) = match opened {
                    Ok(value) => value,
                    Err(message) => {
                        failed.store(true, Ordering::Relaxed);
                        *error.lock().unwrap() = Some(message);
                        return;
                    }
                };
                loop {
                    if failed.load(Ordering::Relaxed) {
                        return;
                    }
                    let row0 = next.fetch_add(STRIP_ROWS, Ordering::Relaxed);
                    if row0 >= program.height {
                        return;
                    }
                    let rows = STRIP_ROWS.min(program.height - row0);
                    if let Err(message) = run_strip(program, &files, &group_masks, row0, rows, stats) {
                        failed.store(true, Ordering::Relaxed);
                        *error.lock().unwrap() = Some(message);
                        return;
                    }
                }
            });
        }
    });
    match error.into_inner().unwrap() {
        Some(message) => Err(message),
        None => Ok(()),
    }
}

/// Runs a program. Returns 0 on success; otherwise writes a message into
/// `error` (UTF-8, truncated to `error_len`) and returns its full length.
/// `stats` receives two counts per program line after the header: pixels
/// that could not match Painter exactly, then pixels that changed.
#[no_mangle]
pub extern "C" fn rizum_painter_look_run(
    program: *const u8,
    program_len: usize,
    threads: usize,
    stats: *mut u64,
    stats_len: usize,
    error: *mut u8,
    error_len: usize,
) -> u64 {
    let result = (|| -> Result<Vec<u64>, String> {
        if program.is_null() {
            return Err("null program".into());
        }
        let text = std::str::from_utf8(unsafe { std::slice::from_raw_parts(program, program_len) })
            .map_err(|_| "program is not UTF-8".to_string())?;
        let parsed = parse_program(text)?;
        if stats_len != parsed.ops.len() * 2 {
            return Err(format!("expected {} statistic slots", parsed.ops.len() * 2));
        }
        let counters = Stats {
            clipped: (0..parsed.ops.len()).map(|_| AtomicU64::new(0)).collect(),
            changed: (0..parsed.ops.len()).map(|_| AtomicU64::new(0)).collect(),
        };
        run(&parsed, threads.max(1), &counters)?;
        Ok(counters.clipped.iter().zip(&counters.changed)
            .flat_map(|(clipped, changed)| [clipped.load(Ordering::Relaxed), changed.load(Ordering::Relaxed)])
            .collect())
    })();
    match result {
        Ok(counts) => {
            if !stats.is_null() {
                unsafe { std::slice::from_raw_parts_mut(stats, counts.len()) }.copy_from_slice(&counts);
            }
            0
        }
        Err(message) => {
            let bytes = message.as_bytes();
            if !error.is_null() && error_len > 0 {
                let n = bytes.len().min(error_len);
                unsafe { std::slice::from_raw_parts_mut(error, n) }.copy_from_slice(&bytes[..n]);
            }
            bytes.len().max(1) as u64
        }
    }
}
