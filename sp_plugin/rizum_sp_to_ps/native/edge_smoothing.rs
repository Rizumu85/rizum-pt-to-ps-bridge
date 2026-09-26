// Morphological antialiasing (MLAA) for exported Painter layers.
//
// The user asked for Clip Studio Paint's smoothing. Measured against a CSP
// export of an aliased test sheet, CSP matches MLAA's area coverage: every
// jagged run is rebuilt as a line from half a pixel past one end to half a
// pixel past the other, each pixel blends with its neighbour across the edge
// by the area that line cuts off, the edge grows outward as much as it shrinks
// inward, and colours blend as encoded (not in linear light). Right-angle
// corners of long straight edges stay untouched, and a one-pixel line stays
// connected through its diagonal steps. Keep those properties when tuning.

use std::mem::size_of;
use std::slice;

const ERROR: u64 = u64::MAX;
/// How far a run is followed each way. Longer shallow runs are treated as
/// open-ended past this, which keeps memory bounded by a window of rows.
const SEARCH: usize = 64;
/// Two premultiplied samples closer than this on every channel are one colour.
const THRESHOLD: f32 = 0.1;
/// Rows an output row reads above and below it: a full vertical search, the
/// pixel past its end, and the one past that for the corner check.
const HALO: usize = SEARCH + 3;
const WINDOW: usize = 2 * HALO + 1;

type Pixel = [f32; 4];

trait Sample: Copy {
    const MAX: f32;

    fn to_f32(self) -> f32;
    fn from_f32(value: f32) -> Self;
}

impl Sample for u8 {
    const MAX: f32 = 255.0;

    fn to_f32(self) -> f32 {
        self as f32
    }

    fn from_f32(value: f32) -> Self {
        value.round().clamp(0.0, <Self as Sample>::MAX) as u8
    }
}

impl Sample for u16 {
    const MAX: f32 = 65_535.0;

    fn to_f32(self) -> f32 {
        self as f32
    }

    fn from_f32(value: f32) -> Self {
        value.round().clamp(0.0, <Self as Sample>::MAX) as u16
    }
}

fn differs(left: Pixel, right: Pixel) -> bool {
    (0..4).any(|channel| (left[channel] - right[channel]).abs() > THRESHOLD)
}

/// Premultiplied copies of the source rows around the row being written.
/// Output rows are written in place, so every read goes through this window of
/// original pixels; a full-image copy would compete with Painter for memory.
struct Rows {
    data: Vec<Pixel>,
    width: usize,
    height: usize,
    loaded: usize,
}

impl Rows {
    fn get(&self, x: isize, y: isize) -> Option<Pixel> {
        if x < 0 || y < 0 || x as usize >= self.width || y as usize >= self.height {
            return None;
        }
        Some(self.data[(y as usize % WINDOW) * self.width + x as usize])
    }
}

/// One edge line seen along its length: `i` runs along the edge, side 0 and
/// side 1 are the pixels on either side of it (j = 0 and j = 1), and j = -1 or
/// j = 2 reach one pixel further out.
struct Line<'a> {
    rows: &'a Rows,
    vertical: bool,
    fixed: isize,
}

impl Line<'_> {
    fn at(&self, i: isize, j: isize) -> Option<Pixel> {
        if self.vertical {
            self.rows.get(self.fixed + j, i)
        } else {
            self.rows.get(i, self.fixed + j)
        }
    }

    fn edge(&self, i: isize) -> Option<(Pixel, Pixel)> {
        let (first, second) = (self.at(i, 0)?, self.at(i, 1)?);
        differs(first, second).then_some((first, second))
    }

    /// The run goes on to `to` while the same two colours face each other,
    /// so a third colour ends it (a T junction) instead of leaking into it.
    fn continues(&self, from: isize, to: isize) -> bool {
        match (self.edge(from), self.edge(to)) {
            (Some((from0, from1)), Some((to0, to1))) => !differs(from0, to0) && !differs(from1, to1),
            _ => false,
        }
    }

    /// Where the edge goes past the run end `inside`, seen at `outside`:
    /// towards side 0 (-0.5), towards side 1 (+0.5) or nowhere (0), and
    /// whether that turn is the corner of a long straight edge.
    fn end(&self, outside: isize, inside: isize) -> (f32, bool) {
        let (Some((first, second)), Some(out0), Some(out1)) =
            (self.edge(inside), self.at(outside, 0), self.at(outside, 1))
        else {
            return (0.0, false);
        };
        let toward0 = !differs(out0, second);
        let toward1 = !differs(out1, first);
        // The turn is long when the crossing edge goes on one more pixel,
        // with both of its colours, not just the outer one.
        let crossing_goes_on = |line: &Self, j: isize, outer: Pixel, inner: Pixel| {
            line.at(outside, j).is_some_and(|pixel| !differs(pixel, outer))
                && line.at(inside, j).is_some_and(|pixel| !differs(pixel, inner))
        };
        let bend0 = |line: &Self| (-0.5, crossing_goes_on(line, -1, second, first));
        let bend1 = |line: &Self| (0.5, crossing_goes_on(line, 2, first, second));
        match (toward0, toward1) {
            (true, false) => bend0(self),
            (false, true) => bend1(self),
            (true, true) => {
                // Both colours step diagonally here, as along a one-pixel
                // line. Keep the thinner colour connected, which is the line.
                let (low, high) = (outside.min(inside) - 1, outside.max(inside) + 1);
                let (mut count0, mut count1) = (0, 0);
                for i in low..=high {
                    for j in -1..=2 {
                        if let Some(pixel) = self.at(i, j) {
                            count0 += (!differs(pixel, first)) as i32;
                            count1 += (!differs(pixel, second)) as i32;
                        }
                    }
                }
                if count1 <= count0 { bend0(self) } else { bend1(self) }
            }
            (false, false) => (0.0, false),
        }
    }

    /// Blend weights at `i`: side 0 towards side 1, and side 1 towards side 0.
    fn weights(&self, i: isize) -> (f32, f32) {
        if self.edge(i).is_none() {
            return (0.0, 0.0);
        }
        let mut before = 0;
        while before < SEARCH && self.continues(i - before as isize, i - before as isize - 1) {
            before += 1;
        }
        let mut after = 0;
        while after < SEARCH && self.continues(i + after as isize, i + after as isize + 1) {
            after += 1;
        }
        let start = i - before as isize;
        let end = i + after as isize + 1;
        // A run longer than the search is open there: no known turn.
        let (mut h0, long0) = if before < SEARCH { self.end(start - 1, start) } else { (0.0, false) };
        let (mut h1, long1) = if after < SEARCH { self.end(end, end - 1) } else { (0.0, false) };
        let step = h0 != 0.0 && h1 != 0.0 && h0 != h1;
        // A one-pixel step joins two runs of the other direction and is
        // smoothed by them; blending it too doubled the weight there. Where
        // both directions step one pixel (45 degrees), CSP keeps the
        // horizontal one.
        if step && end - start == 1 && (self.vertical || long0 || long1) {
            return (0.0, 0.0);
        }
        if !step {
            // A turn onto a long straight edge is a real corner, which CSP
            // leaves square. Only a Z, a step between two runs, still bends
            // there.
            if long0 {
                h0 = 0.0;
            }
            if long1 {
                h1 = 0.0;
            }
        }
        if h0 == 0.0 && h1 == 0.0 {
            return (0.0, 0.0);
        }
        if h0 != 0.0 && h0 == h1 {
            // A U over a one-pixel stroke would eat into the stroke from this
            // side while its other edge does the same; CSP keeps the stroke.
            let (j, other) = if h0 > 0.0 { (2, 0) } else { (-1, 1) };
            let thin = |at: isize| match (self.at(at, j), self.at(at, other)) {
                (Some(beyond), Some(colour)) => !differs(beyond, colour),
                _ => false,
            };
            if thin(start) || thin(end - 1) {
                return (0.0, 0.0);
            }
        }
        let (s, e) = (start as f32, end as f32);
        let profile: &[(f32, f32)] = if h0 != 0.0 && h0 == h1 {
            &[(s, h0), ((s + e) / 2.0, 0.0), (e, h1)]
        } else {
            &[(s, h0), (e, h1)]
        };
        let (toward0, toward1) = coverage(profile, i as f32, i as f32 + 1.0);
        (toward1, toward0)
    }
}

/// Area of the edge profile over [a, b] inside side 1 (h > 0) and inside
/// side 0 (h < 0). Side 1 area takes side 0's colour, and the other way round.
fn coverage(profile: &[(f32, f32)], a: f32, b: f32) -> (f32, f32) {
    let (mut into1, mut into0) = (0.0, 0.0);
    for pair in profile.windows(2) {
        let ((p, hp), (q, hq)) = (pair[0], pair[1]);
        let (low, high) = (a.max(p), b.min(q));
        if high <= low {
            continue;
        }
        let at = |t: f32| hp + (hq - hp) * (t - p) / (q - p);
        let (ha, hb) = (at(low), at(high));
        into1 += positive_area(ha, hb) * (high - low);
        into0 += positive_area(-ha, -hb) * (high - low);
    }
    (into1, into0)
}

/// Mean of max(h, 0) for h linear from `ha` to `hb` over a unit interval.
fn positive_area(ha: f32, hb: f32) -> f32 {
    if ha >= 0.0 && hb >= 0.0 {
        (ha + hb) / 2.0
    } else if ha <= 0.0 && hb <= 0.0 {
        0.0
    } else {
        let crossing = ha / (ha - hb);
        if ha > 0.0 { ha * crossing / 2.0 } else { hb * (1.0 - crossing) / 2.0 }
    }
}

unsafe fn load_row<T: Sample>(rows: &mut Rows, pixels: *mut T, stride: usize) {
    let y = rows.loaded;
    let source = unsafe { slice::from_raw_parts(pixels.add(y * stride), rows.width * 4) };
    let base = (y % WINDOW) * rows.width;
    for x in 0..rows.width {
        let alpha = source[x * 4 + 3].to_f32() / T::MAX;
        let mut pixel = [0.0; 4];
        for channel in 0..3 {
            pixel[channel] = source[x * 4 + channel].to_f32() / T::MAX * alpha;
        }
        pixel[3] = alpha;
        rows.data[base + x] = pixel;
    }
    rows.loaded += 1;
}

unsafe fn smooth<T: Sample>(
    pixels: *mut T,
    width: usize,
    height: usize,
    stride_bytes: usize,
) -> Option<u64> {
    if pixels.is_null() || stride_bytes % size_of::<T>() != 0 {
        return None;
    }
    let stride = stride_bytes / size_of::<T>();
    if stride < width.checked_mul(4)? {
        return None;
    }
    if width < 2 || height < 2 {
        return Some(0);
    }

    let mut rows = Rows {
        data: vec![[0.0; 4]; WINDOW * width],
        width,
        height,
        loaded: 0,
    };
    let mut changed = 0_u64;
    for y in 0..height {
        while rows.loaded < height.min(y + HALO + 1) {
            unsafe { load_row(&mut rows, pixels, stride) };
        }
        let (row, x_count) = (y as isize, width as isize);
        let destination = unsafe { slice::from_raw_parts_mut(pixels.add(y * stride), width * 4) };
        let below = Line { rows: &rows, vertical: false, fixed: row };
        let above = Line { rows: &rows, vertical: false, fixed: row - 1 };
        let base = |y: usize| (y % WINDOW) * width;
        let current = &rows.data[base(y)..base(y) + width];
        let up = (y > 0).then(|| &rows.data[base(y - 1)..base(y - 1) + width]);
        let down = (y + 1 < height).then(|| &rows.data[base(y + 1)..base(y + 1) + width]);
        for x in 0..x_count {
            let index = x as usize;
            let center = current[index];
            // Most pixels sit inside a flat area; only an edge can blend.
            let edged = (index > 0 && differs(center, current[index - 1]))
                || (index + 1 < width && differs(center, current[index + 1]))
                || up.is_some_and(|row| differs(center, row[index]))
                || down.is_some_and(|row| differs(center, row[index]));
            if !edged {
                continue;
            }
            let right = Line { rows: &rows, vertical: true, fixed: x };
            let left = Line { rows: &rows, vertical: true, fixed: x - 1 };
            let blends = [
                (below.weights(x).0, rows.get(x, row + 1)),
                (above.weights(x).1, rows.get(x, row - 1)),
                (right.weights(row).0, rows.get(x + 1, row)),
                (left.weights(row).1, rows.get(x - 1, row)),
            ];
            let total: f32 = blends.iter().map(|(weight, _)| weight).sum();
            if total <= 0.0 {
                continue;
            }
            let scale = if total > 1.0 { 1.0 / total } else { 1.0 };
            let mut output = center.map(|value| value * (1.0 - total * scale));
            for (weight, neighbour) in blends {
                if let Some(neighbour) = neighbour {
                    for channel in 0..4 {
                        output[channel] += neighbour[channel] * weight * scale;
                    }
                }
            }
            let offset = x as usize * 4;
            let alpha = output[3];
            let mut samples = [T::from_f32(0.0); 4];
            samples[3] = T::from_f32(alpha * T::MAX);
            for channel in 0..3 {
                samples[channel] = if alpha > 0.0 {
                    T::from_f32(output[channel] / alpha * T::MAX)
                } else {
                    destination[offset + channel]
                };
            }
            let original = &mut destination[offset..offset + 4];
            if (0..4).any(|channel| samples[channel].to_f32() != original[channel].to_f32()) {
                original.copy_from_slice(&samples);
                changed += 1;
            }
        }
    }

    Some(changed)
}

#[no_mangle]
pub extern "C" fn rizum_smooth_rgba8(
    pixels: *mut u8,
    width: usize,
    height: usize,
    stride_bytes: usize,
) -> u64 {
    unsafe { smooth(pixels, width, height, stride_bytes) }.unwrap_or(ERROR)
}

#[no_mangle]
pub extern "C" fn rizum_smooth_rgba16(
    pixels: *mut u16,
    width: usize,
    height: usize,
    stride_bytes: usize,
) -> u64 {
    unsafe { smooth(pixels, width, height, stride_bytes) }.unwrap_or(ERROR)
}
