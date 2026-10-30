
  import {EditorView, minimalSetup} from "codemirror"
  import {StateField} from "@codemirror/state"
  import {placeholder} from "@codemirror/view"
  import {sql} from "@codemirror/lang-sql"
  import {oneDark} from "@codemirror/theme-one-dark"

  window.createCodeMirrorEditor = function(el) {
    const doc = el.textContent.trim();
    el.innerHTML = "";
    const extensions = [minimalSetup, sql(), EditorView.lineWrapping, placeholder("Type your SQLETL query here...")];

    if (el.hasAttribute("data-hasname")) {
      const textarea = el.nextElementSibling
      textarea.value = doc;
      let updateTextarea = StateField.define({
        create() { return 0 },
        update(value, tr) {
          if (tr.docChanged) {
            textarea.value = tr.newDoc.toString()
          }
          return 0;
        }
      })
      extensions.push(updateTextarea)
    }

    if (document.documentElement.getAttribute('data-theme') == "dark") {
      extensions.push(oneDark)
    }

    const view = new EditorView({
      doc,
      extensions,
      parent: el
    })
    view.dom.style.height = "100%";
    if (el.id) {
      window.sqleditors = window.sqleditors || {};
      window.sqleditors[el.id] = function(text) {
        view.dispatch({
          changes: {from: 0, to: view.state.doc.length, insert: text}
        });
      };
    }
  };
