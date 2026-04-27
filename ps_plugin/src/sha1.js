"use strict";

function createSha1() {
  return new Sha1();
}

function sha1ArrayBuffer(buffer) {
  return createSha1().update(new Uint8Array(buffer)).digest();
}

class Sha1 {
  constructor() {
    this.h0 = 0x67452301;
    this.h1 = 0xefcdab89;
    this.h2 = 0x98badcfe;
    this.h3 = 0x10325476;
    this.h4 = 0xc3d2e1f0;
    this.block = new Uint8Array(64);
    this.blockLength = 0;
    this.totalLength = 0;
    this.words = new Array(80);
    this.finished = false;
  }

  update(input) {
    if (this.finished) {
      throw new Error("Cannot update SHA-1 after digest");
    }

    const bytes = toUint8Array(input);
    this.totalLength += bytes.length;
    let offset = 0;

    while (offset < bytes.length) {
      const available = 64 - this.blockLength;
      const count = Math.min(available, bytes.length - offset);
      this.block.set(bytes.subarray(offset, offset + count), this.blockLength);
      this.blockLength += count;
      offset += count;

      if (this.blockLength === 64) {
        this.processBlock(this.block);
        this.blockLength = 0;
      }
    }

    return this;
  }

  digest() {
    if (this.finished) {
      throw new Error("SHA-1 digest already called");
    }
    this.finished = true;

    const bitLengthHigh = Math.floor((this.totalLength * 8) / 0x100000000);
    const bitLengthLow = (this.totalLength * 8) >>> 0;

    this.block[this.blockLength] = 0x80;
    this.blockLength += 1;

    if (this.blockLength > 56) {
      this.block.fill(0, this.blockLength, 64);
      this.processBlock(this.block);
      this.blockLength = 0;
    }

    this.block.fill(0, this.blockLength, 56);
    writeUint32BE(this.block, 56, bitLengthHigh);
    writeUint32BE(this.block, 60, bitLengthLow);
    this.processBlock(this.block);

    return [this.h0, this.h1, this.h2, this.h3, this.h4].map(wordToHex).join("");
  }

  processBlock(block) {
    const words = this.words;
    for (let i = 0; i < 16; i += 1) {
      const offset = i * 4;
      words[i] = (
        (block[offset] << 24) |
        (block[offset + 1] << 16) |
        (block[offset + 2] << 8) |
        block[offset + 3]
      ) >>> 0;
    }
    for (let i = 16; i < 80; i += 1) {
      words[i] = rotateLeft(words[i - 3] ^ words[i - 8] ^ words[i - 14] ^ words[i - 16], 1);
    }

    let a = this.h0;
    let b = this.h1;
    let c = this.h2;
    let d = this.h3;
    let e = this.h4;

    for (let i = 0; i < 80; i += 1) {
      const temp = add32(add32(add32(add32(rotateLeft(a, 5), sha1Function(i, b, c, d)), e), words[i]), sha1Constant(i));
      e = d;
      d = c;
      c = rotateLeft(b, 30);
      b = a;
      a = temp;
    }

    this.h0 = add32(this.h0, a);
    this.h1 = add32(this.h1, b);
    this.h2 = add32(this.h2, c);
    this.h3 = add32(this.h3, d);
    this.h4 = add32(this.h4, e);
  }
}

function toUint8Array(input) {
  if (input instanceof Uint8Array) {
    return input;
  }
  if (input instanceof ArrayBuffer) {
    return new Uint8Array(input);
  }
  if (ArrayBuffer.isView(input)) {
    return new Uint8Array(input.buffer, input.byteOffset, input.byteLength);
  }
  throw new Error("SHA-1 update expects an ArrayBuffer or typed array");
}

function writeUint32BE(bytes, offset, value) {
  bytes[offset] = (value >>> 24) & 0xff;
  bytes[offset + 1] = (value >>> 16) & 0xff;
  bytes[offset + 2] = (value >>> 8) & 0xff;
  bytes[offset + 3] = value & 0xff;
}

function sha1Function(i, b, c, d) {
  if (i < 20) {
    return (b & c) | (~b & d);
  }
  if (i < 40) {
    return b ^ c ^ d;
  }
  if (i < 60) {
    return (b & c) | (b & d) | (c & d);
  }
  return b ^ c ^ d;
}

function sha1Constant(i) {
  if (i < 20) {
    return 0x5a827999;
  }
  if (i < 40) {
    return 0x6ed9eba1;
  }
  if (i < 60) {
    return 0x8f1bbcdc;
  }
  return 0xca62c1d6;
}

function rotateLeft(value, bits) {
  return ((value << bits) | (value >>> (32 - bits))) >>> 0;
}

function add32(left, right) {
  return (left + right) >>> 0;
}

function wordToHex(word) {
  return (word >>> 0).toString(16).padStart(8, "0");
}

module.exports = {
  createSha1,
  sha1ArrayBuffer
};
