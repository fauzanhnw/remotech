import { useCallback, useMemo, useRef, useState } from 'react'
import ReactQuill from 'react-quill-new'
import 'react-quill-new/dist/quill.snow.css'
import { Input, Modal } from 'antd'

import { notifyError, notifyInfo, uploadImage } from '@/api'
import { toEmbedUrl } from '@/utils/video'

interface RichTextEditorProps {
  value?: string
  onChange?: (value: string) => void
  placeholder?: string
}

/**
 * Toolbar sengaja hanya memakai format yang diizinkan sanitizer backend
 * (richtext.py): heading, bold/italic/underline/strike, align (text-align),
 * list, quote, code, link, image, video (iframe host EMBED_HOSTS).
 * Tanpa color/background — style-nya dibuang.
 */
const TOOLBAR = [
  [{ header: [1, 2, 3, false] }],
  ['bold', 'italic', 'underline', 'strike'],
  [{ align: [] }],
  [{ list: 'ordered' }, { list: 'bullet' }],
  ['blockquote', 'code-block'],
  ['link', 'image', 'video'],
  ['clean'],
]

/** Quill menghasilkan `<p><br></p>` saat kosong — normalkan agar validasi required akurat. */
function normalizeHtml(html: string): string {
  if (!html) return ''
  if (/<img\b|<iframe\b/i.test(html)) return html
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
  const [videoOpen, setVideoOpen] = useState(false)
  const [videoUrl, setVideoUrl] = useState('')
  const videoIndexRef = useRef(0)
  const pendingEmbedRef = useRef<string | null>(null)

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

  const openVideoModal = useCallback(() => {
    const editor = quillRef.current?.getEditor()
    if (!editor) return
    const range = editor.getSelection()
    videoIndexRef.current = range?.index ?? editor.getLength()
    setVideoUrl('')
    setVideoOpen(true)
  }, [])

  const insertVideo = useCallback(() => {
    const embed = toEmbedUrl(videoUrl.trim())
    if (!embed) {
      notifyError('Link video belum didukung. Gunakan link YouTube atau Google Drive.')
      return
    }
    pendingEmbedRef.current = embed
    setVideoOpen(false)
  }, [videoUrl])

  // Insert setelah modal benar-benar tertutup agar fokus tidak direbut kembali Modal.
  const handleVideoModalClosed = useCallback(() => {
    const embed = pendingEmbedRef.current
    pendingEmbedRef.current = null
    const editor = quillRef.current?.getEditor()
    if (!embed || !editor) return
    const index = videoIndexRef.current
    editor.insertEmbed(index, 'video', embed, 'user')
    editor.setSelection(index + 1)
    editor.focus()
  }, [])

  const modules = useMemo(
    () => ({
      toolbar: { container: TOOLBAR, handlers: { image: handleImage, video: openVideoModal } },
    }),
    [handleImage, openVideoModal],
  )

  return (
    <div className="rounded-md border border-gray-300 bg-white [&_.ql-editor]:min-h-40 [&_.ql-editor]:px-3 [&_.ql-editor]:text-base [&_.ql-toolbar.ql-snow]:rounded-t-md [&_.ql-toolbar.ql-snow]:border-x-0 [&_.ql-toolbar.ql-snow]:border-t-0 [&_.ql-container.ql-snow]:border-0">
      <ReactQuill
        ref={quillRef}
        theme="snow"
        value={value ?? ''}
        modules={modules}
        placeholder={placeholder}
        // getSemanticHTML() (default) mengubah blot video menjadi <a href>;
        // root.innerHTML menyimpan <iframe> apa adanya dan spasi biasa (bukan &nbsp;).
        useSemanticHTML={false}
        onChange={(html) => onChange?.(normalizeHtml(html))}
      />
      <Modal
        open={videoOpen}
        title="Embed video"
        okText="Insert"
        onOk={insertVideo}
        onCancel={() => setVideoOpen(false)}
        afterClose={handleVideoModalClosed}
        destroyOnHidden
      >
        <Input
          placeholder="https://www.youtube.com/watch?v=... atau https://drive.google.com/file/d/.../view"
          value={videoUrl}
          onChange={(event) => setVideoUrl(event.target.value)}
          onPressEnter={insertVideo}
          autoFocus
        />
      </Modal>
    </div>
  )
}
