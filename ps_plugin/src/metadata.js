"use strict";

const UID_SUFFIX_PREFIX = "\u2021";
const SIDECAR_EXTENSION = ".rizum.json";

function formatUidSuffix(uidHex) {
  return `${UID_SUFFIX_PREFIX}${uidHex}`;
}

module.exports = {
  UID_SUFFIX_PREFIX,
  SIDECAR_EXTENSION,
  formatUidSuffix
};
