use std::mem::size_of;
use std::slice;

const ERROR: u64 = u64::MAX;

trait Sample: Copy + Eq {
    const MAX: u32;
    const COLOR_THRESHOLD: u32;
    const ALPHA_THRESHOLD: u32;

    fn to_u32(self) -> u32;
    fn from_u32(value: u32) -> Self;
}

impl Sample for u8 {
    const MAX: u32 = 255;
    const COLOR_THRESHOLD: u32 = 42;
    const ALPHA_THRESHOLD: u32 = 200;

    fn to_u32(self) -> u32 {
        self as u32
    }

    fn from_u32(value: u32) -> Self {
        value.min(<Self as Sample>::MAX) as u8
    }
}

impl Sample for u16 {
    const MAX: u32 = 65_535;
    const COLOR_THRESHOLD: u32 = 42 * 257;
    const ALPHA_THRESHOLD: u32 = 200 * 257;

    fn to_u32(self) -> u32 {
        self as u32
    }

    fn from_u32(value: u32) -> Self {
        value.min(<Self as Sample>::MAX) as u16
    }
}

fn pixel<T: Sample>(row: &[T], x: usize) -> [T; 4] {
    let offset = x * 4;
    [
        row[offset],
        row[offset + 1],
        row[offset + 2],
        row[offset + 3],
    ]
}

fn similar<T: Sample>(left: [T; 4], right: [T; 4]) -> bool {
    let left_alpha = left[3].to_u32();
    let right_alpha = right[3].to_u32();
    if left_alpha == 0 && right_alpha == 0 {
        return true;
    }
    if left_alpha.abs_diff(right_alpha) > T::ALPHA_THRESHOLD {
        return false;
    }

    (0..3)
        .map(|channel| left[channel].to_u32().abs_diff(right[channel].to_u32()))
        .sum::<u32>()
        <= T::COLOR_THRESHOLD
}

fn average_premultiplied<T: Sample>(samples: [[T; 4]; 4]) -> [T; 4] {
    let alpha_sum = samples
        .iter()
        .map(|sample| sample[3].to_u32() as u64)
        .sum::<u64>();
    if alpha_sum == 0 {
        return [T::from_u32(0); 4];
    }

    let mut output = [T::from_u32(0); 4];
    for channel in 0..3 {
        let premultiplied_sum = samples
            .iter()
            .map(|sample| sample[channel].to_u32() as u64 * sample[3].to_u32() as u64)
            .sum::<u64>();
        output[channel] = T::from_u32(((premultiplied_sum + alpha_sum / 2) / alpha_sum) as u32);
    }
    output[3] = T::from_u32(((alpha_sum + 2) / 4) as u32);
    output
}

unsafe fn copy_row<T: Sample>(pixels: *mut T, y: usize, stride: usize, width: usize) -> Vec<T> {
    unsafe { slice::from_raw_parts(pixels.add(y * stride), width * 4) }.to_vec()
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
    if width < 3 || height < 3 {
        return Some(0);
    }

    // Three source rows preserve linear memory use for 8K exports. A full-image
    // copy would make this small quality pass compete with Painter for gigabytes.
    let mut previous = unsafe { copy_row(pixels, 0, stride, width) };
    let mut current = unsafe { copy_row(pixels, 1, stride, width) };
    let mut next = unsafe { copy_row(pixels, 2, stride, width) };
    let mut changed = 0_u64;

    for y in 1..height - 1 {
        let destination = unsafe { slice::from_raw_parts_mut(pixels.add(y * stride), width * 4) };
        for x in 1..width - 1 {
            let north = pixel(&previous, x);
            let west = pixel(&current, x - 1);
            let center = pixel(&current, x);
            let east = pixel(&current, x + 1);
            let south = pixel(&next, x);

            if similar(north, south) || similar(west, east) {
                continue;
            }

            let quadrants = [
                if similar(west, north) { west } else { center },
                if similar(north, east) { east } else { center },
                if similar(west, south) { west } else { center },
                if similar(south, east) { east } else { center },
            ];
            let filtered = average_premultiplied(quadrants);
            if filtered != center {
                changed += 1;
                let offset = x * 4;
                destination[offset..offset + 4].copy_from_slice(&filtered);
            }
        }

        if y + 1 < height - 1 {
            previous = current;
            current = next;
            next = unsafe { copy_row(pixels, y + 2, stride, width) };
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
