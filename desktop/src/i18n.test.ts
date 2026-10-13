import { readdirSync, readFileSync } from "node:fs"
import path from "node:path"
import { afterEach, describe, expect, it } from "vitest"
import { languages, resolveLanguage, setLanguage, t, translations } from "./i18n"

const sources = readdirSync(import.meta.dirname)
  .filter(name => /\.tsx?$/.test(name) && !name.includes(".test.") && name !== "i18n.ts")
  .map(name => readFileSync(path.join(import.meta.dirname, name), "utf8"))
// t("…") and the singular/plural form t(one ? "…" : "…").
const call = /\bt\((?:[^"\n]*\? )?"((?:[^"\\]|\\.)*)"(?: : "((?:[^"\\]|\\.)*)")?/g
const used = new Set(sources.flatMap(text => [...text.matchAll(call)].flatMap(match => match.slice(1).filter(Boolean))))
const placeholders = (text: string) => [...text.matchAll(/\{\w+\}/g)].map(match => match[0]).sort()

describe("window language", () => {
  afterEach(() => setLanguage("en"))

  it("has every sentence the window shows in every language, with its values", () => {
    expect(used.size).toBeGreaterThan(80)
    for (const source of used) {
      const row = translations[source]
      expect(row, source).toBeDefined()
      expect(row.length, source).toBe(languages.length - 1)
      for (const translated of row) {
        expect(translated.trim(), source).not.toBe("")
        expect(placeholders(translated), `${source} -> ${translated}`).toEqual(placeholders(source))
      }
    }
  })

  it("keeps no sentence the window stopped showing", () => {
    expect(Object.keys(translations).filter(source => !used.has(source))).toEqual([])
  })

  it("follows Painter's language code and falls back to English", () => {
    expect(resolveLanguage("zh-CN")).toBe("zh")
    expect(resolveLanguage("pt_BR")).toBe("pt")
    expect(resolveLanguage("xx")).toBe("en")
    setLanguage("zh")
    expect(t("{count} to delete", { count: 2 })).toBe("2 个待删除")
    expect(t("Not a sentence the window has")).toBe("Not a sentence the window has")
    setLanguage("en")
    expect(t("{count} to delete", { count: 2 })).toBe("2 to delete")
  })
})
