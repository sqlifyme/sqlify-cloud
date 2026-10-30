import {EditorView, minimalSetup} from "codemirror"
import {placeholder} from "@codemirror/view"
import {sql} from "@codemirror/lang-sql"
import {oneDark} from "@codemirror/theme-one-dark"

class SQLEditor extends HTMLElement {
  static formAssociated = true

  constructor() {
    super()
    this.internals = this.attachInternals()
  }

  connectedCallback() {
    if (this.view) return
    const doc = this.textContent.trim()
    this.innerHTML = ""
    const extensions = [
      minimalSetup,
      sql(),
      EditorView.lineWrapping,
      placeholder("Type your SQLETL query here..."),
      EditorView.updateListener.of(update => {
        if (update.docChanged) this.internals.setFormValue(update.state.doc.toString())
      }),
    ]

    if (document.documentElement.getAttribute('data-theme') == "dark") {
      extensions.push(oneDark)
    }

    this.view = new EditorView({doc, extensions, parent: this})
    this.view.dom.style.height = "100%"
    this.internals.setFormValue(doc)
  }

  get name() {
    return this.getAttribute("name")
  }

  get form() {
    return this.internals.form
  }

  get value() {
    return this.view ? this.view.state.doc.toString() : this.textContent.trim()
  }

  set value(text) {
    if (!this.view) {
      this.textContent = text
      return
    }
    this.view.dispatch({changes: {from: 0, to: this.view.state.doc.length, insert: text}})
  }
}

customElements.define("sql-editor", SQLEditor)
