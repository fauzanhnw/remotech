import { useCallback, useMemo, useRef } from 'react'
import ReactQuill from 'react-quill-new'
import 'react-quill-new/dist/quill.snow.css'

import { notifyError, notifyInfo, uploadImage } from '@/api'

interface RichTextEditorProps {
  value?: string
  onChange?: (value: string) => void
  placeholder?: string
}

/**
 * Toolbar sengaja hanya memakai format yang diizinkan sanitizer backend
 * (richtext.py): heading, bold/italic/underline/strike, align (text-align),
 * list, quote, code, link, image. Tanpa color/background — style-nya dibuang.
 */
const TOOLBAR = [
  [{ header: [1, 2, 3, false] }],
  ['bold', 'italic', 'underline', 'strike'],
  [{ align: [] }],
  [{ list: 'ordered' }, { list: 'bullet' }],
  ['blockquote', 'code-block'],
  ['link', 'image'],
  ['clean'],
]

/** Quill menghasilkan `<p><br></p>` saat kosong — normalkan agar validasi required akurat. */
function normalizeHtml(html: string): string {
  if (!html) return ''
  if (/<img\b/i.test(html)) return html
  const text = html
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return text === '' ? '' : html
}

/** Editor rich text (Quill 2) untuk konten module — output HTML bersih. */
export function RichTextEditor({ value, onChange, placeholder }: RichTextEditorProps) {
  const quillRef = useRef<ReactQuill>(null)

  const handleImage = useCallback(() => {
    const editor = quillRef.current?.getEditor()
    if (!editor) return

    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*'
    input.onchange = () => {
      const file = input.files?.[0]
      if (!file) return

      notifyInfo('Uploading image...')
      uploadImage(file)
        .then(({ url }) => {
          const range = editor.getSelection()
          const index = range?.index ?? editor.getLength()
          editor.insertEmbed(index, 'image', url, 'user')
          editor.setSelection(index + 1)
        })
        .catch((error) => notifyError(error))
    }
    input.click()
  }, [])

  const modules = useMemo(
    () => ({
      toolbar: { container: TOOLBAR, handlers: { image: handleImage } },
    }),
    [handleImage],
  )

  return (
    <div className="rounded-md border border-gray-300 bg-white [&_.ql-editor]:min-h-40 [&_.ql-editor]:px-3 [&_.ql-editor]:text-base [&_.ql-toolbar.ql-snow]:rounded-t-md [&_.ql-toolbar.ql-snow]:border-x-0 [&_.ql-toolbar.ql-snow]:border-t-0 [&_.ql-container.ql-snow]:border-0">
      <ReactQuill
        ref={quillRef}
        theme="snow"
        value={value ?? ''}
        modules={modules}
        placeholder={placeholder}
        onChange={(html) => onChange?.(normalizeHtml(html))}
      />
    </div>
  )
}
