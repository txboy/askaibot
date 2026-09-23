import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/atom-one-light.css'

const md = new MarkdownIt({
  linkify: true,
  breaks: true,
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang, ignoreIllegals: true }).value
      } catch {}
    }
    return ''
  },
})

export function renderMarkdown(text) {
  return md.render(text || '')
}
