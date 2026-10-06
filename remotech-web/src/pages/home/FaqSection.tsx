import { Collapse } from 'antd'

import { faqs } from './data'

/** Daftar pertanyaan umum program. */
export function FaqSection() {
  return (
    <section id="faq" className="mx-auto max-w-4xl px-4 py-16 md:py-10">
      <h2 className="text-center text-3xl font-bold text-[#08060d] md:text-4xl py-5">
        Pertanyaan yang Sering Diajukan
      </h2>
      <Collapse
        className="mt-8"
        style={{ backgroundColor: '#fff', borderColor: '#e5e7eb', borderRadius: 12 }}
        items={faqs.map((faq) => ({
          key: faq.question,
          label: <span className="font-medium">{faq.question}</span>,
          children: <p className="leading-relaxed text-gray-600">{faq.answer}</p>,
        }))}
      />
    </section>
  )
}
