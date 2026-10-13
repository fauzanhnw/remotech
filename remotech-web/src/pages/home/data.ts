/** Seluruh copy statis halaman Home — ubah teks di sini tanpa menyentuh JSX. */

export interface Stat {
  value: string
  label: string
}

export interface FeatureCard {
  icon: 'modules' | 'assignments' | 'gamification'
  title: string
  description: string
}

export interface FaqItem {
  question: string
  answer: string
}

export const hero = {
  eyebrow: 'REMOTE CIRCLE COMMUNITY',
  title: 'Pelajari Remote Working Melalui Remote Challenge',
  subtitle:
    'Bergabunglah dengan Remote Circle dalam tantangan belajar bersama: modul terstruktur, tugas praktis, dan papan peringkat yang menggerakkan seluruh komunitas.',
  tagline: 'Ikuti tantangan. Selesaikan. Maju bersama komunitas.',
  ctaLabel: 'Mulai Sekarang',
}

export const stats: Stat[] = [
  { value: '7%', label: 'Porsi hari kerja penuh yang dilakukan remote pada 2019' },
  { value: '28%', label: 'Porsi hari kerja penuh yang remote pada pertengahan 2023' },
  { value: '2028', label: 'Tren diproyeksikan terus meningkat hingga' },
]

export const statsSource = ''

export const features = {
  eyebrow: 'SATU PLATFORM',
  title: 'Semua yang kamu butuhkan, dalam satu tempat',
  description:
    'Remote Challenge menyatukan materi pembelajaran, tugas, penilaian, poin, dan papan peringkat dalam satu platform.',
  linkLabel: 'Lihat Courses',
  cards: [
    {
      icon: 'modules',
      title: 'Modul Terstruktur',
      description: 'Pelajaran teks dan video yang tersusun berurutan, dengan progresmu dilacak modul demi modul.',
    },
    {
      icon: 'assignments',
      title: 'Tugas Nyata',
      description: 'Kirim hasil kerjamu lewat tautan, lalu dapat ditinjau dan dinilai oleh mentor.',
    },
    {
      icon: 'gamification',
      title: 'Progres Berbasis Gamifikasi',
      description:
        'Dapatkan poin di setiap modul yang selesai, naik di papan peringkat, dan kumpulkan badge — setiap langkahmu menambah capaian Remote Circle.',
    },
  ] satisfies FeatureCard[],
}

export const faqs: FaqItem[] = [
  {
    question: 'Apa itu Remote Challenge?',
    answer:
      'Remote Challenge adalah program inkubator intensif dari Remote Circle Community. Melalui sesi daring, modul pembelajaran terstruktur, dan tugas praktis. Peserta berupaya mendapatkan pekerjaan remote selama periode program berlangsung.',
  },
  {
    question: 'Untuk siapa program ini?',
    answer:
      'Siapa pun yang ingin memulai atau mempercepat karier remote, termasuk pemula yang belum pernah bekerja remote. Materi dan tugas dirancang untuk membangun keterampilan dan portofolio yang dicari oleh pemberi kerja remote.',
  },
  {
    question: 'Apakah saya perlu pengalaman kerja remote terlebih dahulu?',
    answer:
      'Tidak. Program ini tidak mengasumsikan adanya pengalaman remote sebelumnya. Yang kamu butuhkan adalah konsistensi: selesaikan modul, kirim tugas tepat waktu, dan terapkan umpan balik dari mentor.',
  },
  {
    question: 'Bagaimana poin dan papan peringkat bekerja?',
    answer:
      'Kamu mendapatkan poin setiap kali menyelesaikan modul atau tugas. Poin tercatat di riwayat progresmu dan diranking di papan peringkat, sehingga kamu bisa melihat posisimu dibanding peserta lain secara real-time — satu papan peringkat yang kamu isi bersama peserta Remote Circle lainnya.',
  },
  {question: "Apakah semua course sepenuhnya gratis?",
    answer: "Tidak. Beberapa course memang sepenuhnya gratis, namun ada course yang berbayar."
  },
  {
    question: 'Bagaimana cara memulai?',
    answer: 'Kamu perlu membuat akun terlebih dahulu untuk mengakses lebih banyak. Enroll course yang diinginkan, dan selesaikan modul materinya.',
  },
]

export const cta = {
  title: 'Siap mengikuti tantangan?',
  description: 'Buat akunmu dan mulai Remote Challenge hari ini.',
  primaryLabel: 'Mulai Sekarang',
  secondaryLabel: 'Lihat Courses',
}
