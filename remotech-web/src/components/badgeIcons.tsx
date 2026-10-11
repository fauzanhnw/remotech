import {
  AimOutlined,
  BookOutlined,
  BugOutlined,
  BulbOutlined,
  CalendarOutlined,
  CameraOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloudServerOutlined,
  CodeOutlined,
  CoffeeOutlined,
  CompassOutlined,
  CrownOutlined,
  DislikeOutlined,
  DockerOutlined,
  ExperimentOutlined,
  FireOutlined,
  FlagOutlined,
  FrownOutlined,
  GiftOutlined,
  GithubOutlined,
  GoldOutlined,
  HeartOutlined,
  HourglassOutlined,
  Html5Outlined,
  JavaOutlined,
  JavaScriptOutlined,
  LikeOutlined,
  MehOutlined,
  MobileOutlined,
  MoneyCollectOutlined,
  PayCircleOutlined,
  PictureOutlined,
  PlusCircleOutlined,
  ProfileOutlined,
  PythonOutlined,
  ReadOutlined,
  RobotOutlined,
  RocketOutlined,
  SafetyCertificateOutlined,
  SafetyOutlined,
  ScheduleOutlined,
  ShoppingCartOutlined,
  SmileOutlined,
  StarOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  TrophyOutlined,
  UserAddOutlined,
  UsergroupAddOutlined,
  VideoCameraOutlined,
  WalletOutlined,
  GlobalOutlined,
} from '@ant-design/icons'
import type { ReactNode } from 'react'

/**
 * Ikon preset badge (dipilih mentor lewat `icon_name`).
 *
 * Daftar bisa ditambah kapan saja tanpa migration — cukup tambah entri di
 * sini dan di BADGE_ICON_GROUPS. Nama yang tidak dikenal jatuh ke trophy.
 */
export const BADGE_ICONS: Record<string, ReactNode> = {
  trophy: <TrophyOutlined />,
  gold: <GoldOutlined />,
  crown: <CrownOutlined />,
  star: <StarOutlined />,
  flag: <FlagOutlined />,
  like: <LikeOutlined />,
  dislike: <DislikeOutlined />,
  safety_certificate: <SafetyCertificateOutlined />,
  fire: <FireOutlined />,
  thunderbolt: <ThunderboltOutlined />,
  rocket: <RocketOutlined />,
  aim: <AimOutlined />,
  clock: <ClockCircleOutlined />,
  calendar: <CalendarOutlined />,
  hourglass: <HourglassOutlined />,
  schedule: <ScheduleOutlined />,
  safety: <SafetyOutlined />,
  check_circle: <CheckCircleOutlined />,
  plus_circle: <PlusCircleOutlined />,
  heart: <HeartOutlined />,
  gift: <GiftOutlined />,
  smile: <SmileOutlined />,
  meh: <MehOutlined />,
  frown: <FrownOutlined />,
  read: <ReadOutlined />,
  book: <BookOutlined />,
  bulb: <BulbOutlined />,
  experiment: <ExperimentOutlined />,
  code: <CodeOutlined />,
  bug: <BugOutlined />,
  profile: <ProfileOutlined />,
  team: <TeamOutlined />,
  usergroup: <UsergroupAddOutlined />,
  user_add: <UserAddOutlined />,
  robot: <RobotOutlined />,
  python: <PythonOutlined />,
  java: <JavaOutlined />,
  javascript: <JavaScriptOutlined />,
  html5: <Html5Outlined />,
  github: <GithubOutlined />,
  docker: <DockerOutlined />,
  cloud_server: <CloudServerOutlined />,
  coffee: <CoffeeOutlined />,
  camera: <CameraOutlined />,
  picture: <PictureOutlined />,
  video: <VideoCameraOutlined />,
  global: <GlobalOutlined />,
  compass: <CompassOutlined />,
  money: <MoneyCollectOutlined />,
  wallet: <WalletOutlined />,
  pay: <PayCircleOutlined />,
  cart: <ShoppingCartOutlined />,
  mobile: <MobileOutlined />,
}

interface BadgeIconGroup {
  label: string
  values: { value: string; label: string }[]
}

const iconOption = (value: string, label: string) => ({ value, label })

/** Opsi ikon dikelompokkan untuk Select mentor. */
export const BADGE_ICON_GROUPS: BadgeIconGroup[] = [
  {
    label: 'Prestasi',
    values: [
      iconOption('trophy', 'Trophy'),
      iconOption('gold', 'Gold'),
      iconOption('crown', 'Crown'),
      iconOption('star', 'Star'),
      iconOption('flag', 'Flag'),
      iconOption('like', 'Like'),
      iconOption('safety_certificate', 'Certificate'),
    ],
  },
  {
    label: 'Semangat',
    values: [
      iconOption('fire', 'Fire'),
      iconOption('thunderbolt', 'Thunderbolt'),
      iconOption('rocket', 'Rocket'),
      iconOption('aim', 'Aim'),
    ],
  },
  {
    label: 'Waktu',
    values: [
      iconOption('clock', 'Clock'),
      iconOption('calendar', 'Calendar'),
      iconOption('hourglass', 'Hourglass'),
      iconOption('schedule', 'Schedule'),
    ],
  },
  {
    label: 'Status',
    values: [
      iconOption('safety', 'Safety'),
      iconOption('check_circle', 'Check'),
      iconOption('plus_circle', 'Plus'),
      iconOption('heart', 'Heart'),
      iconOption('gift', 'Gift'),
    ],
  },
  {
    label: 'Emosi',
    values: [
      iconOption('smile', 'Smile'),
      iconOption('meh', 'Meh'),
      iconOption('frown', 'Frown'),
    ],
  },
  {
    label: 'Belajar',
    values: [
      iconOption('read', 'Read'),
      iconOption('book', 'Book'),
      iconOption('bulb', 'Bulb'),
      iconOption('experiment', 'Experiment'),
      iconOption('code', 'Code'),
      iconOption('bug', 'Bug'),
      iconOption('profile', 'Profile'),
    ],
  },
  {
    label: 'Tim',
    values: [
      iconOption('team', 'Team'),
      iconOption('usergroup', 'User group'),
      iconOption('user_add', 'User add'),
    ],
  },
  {
    label: 'Teknologi',
    values: [
      iconOption('python', 'Python'),
      iconOption('java', 'Java'),
      iconOption('javascript', 'JavaScript'),
      iconOption('html5', 'HTML5'),
      iconOption('github', 'GitHub'),
      iconOption('docker', 'Docker'),
      iconOption('cloud_server', 'Cloud'),
    ],
  },
  {
    label: 'Gaya hidup',
    values: [
      iconOption('coffee', 'Coffee'),
      iconOption('camera', 'Camera'),
      iconOption('picture', 'Picture'),
      iconOption('video', 'Video'),
      iconOption('global', 'Global'),
      iconOption('compass', 'Compass'),
      iconOption('mobile', 'Mobile'),
    ],
  },
  {
    label: 'Ekonomi',
    values: [
      iconOption('money', 'Money'),
      iconOption('wallet', 'Wallet'),
      iconOption('pay', 'Pay'),
      iconOption('cart', 'Cart'),
    ],
  },
]

/** Render ikon preset; nama tak dikenal → trophy. */
export function badgeIconNode(iconName: string): ReactNode {
  return BADGE_ICONS[iconName] ?? BADGE_ICONS.trophy
}
