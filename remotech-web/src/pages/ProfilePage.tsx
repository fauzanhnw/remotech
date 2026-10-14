import { LockOutlined, MailOutlined, TrophyOutlined, UserOutlined } from '@ant-design/icons'
import { Button, Form, Input, Skeleton, Tag } from 'antd'
import type { FormInstance } from 'antd'
import { useEffect, useState } from 'react'

import {
  changePassword,
  getMyLeaderboard,
  getFieldErrors,
  notifyError,
  notifySuccess,
  updateProfile,
} from '@/api'
import { useAuth } from '@/auth/AuthContext'
import { BadgeGrid } from '@/components/BadgeGrid'
import { usePageTitle } from '@/hooks/usePageTitle'
import { levelColor, levelLabel } from '@/utils/level'

interface ProfileValues {
  first_name: string
  last_name: string
  email: string
}

interface PasswordValues {
  old_password: string
  new_password: string
  new_password_confirm: string
}

/** Petakan error validasi backend ke field form; sisanya tampilkan toast. */
function applyFieldErrors(form: FormInstance, error: unknown): void {
  const entries = Object.entries(getFieldErrors(error))
  if (entries.length === 0) {
    notifyError(error)
    return
  }
  form.setFields(entries.map(([name, help]) => ({ name, errors: [help] })))
}

export function ProfilePage() {
  usePageTitle('Profile')
  const { user, profileLoaded, refreshUser } = useAuth()
  const [profileForm] = Form.useForm<ProfileValues>()
  const [passwordForm] = Form.useForm<PasswordValues>()
  const [savingProfile, setSavingProfile] = useState(false)
  const [savingPassword, setSavingPassword] = useState(false)
  const [level, setLevel] = useState<{ level: number; title: string } | null>(null)

  // Level on-the-fly dari total poin (gagal senyap — kartu tetap tampil).
  useEffect(() => {
    if (!user) return
    let cancelled = false
    getMyLeaderboard()
      .then((data) => {
        if (!cancelled) {
          setLevel({ level: data.level, title: data.level_title })
        }
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [user])

  // Isi ulang form tiap profil berubah (mis. setelah refreshUser).
  useEffect(() => {
    if (!user) return
    profileForm.setFieldsValue({
      first_name: user.first_name,
      last_name: user.last_name,
      email: user.email,
    })
  }, [user, profileForm])

  const handleProfileSubmit = async (values: ProfileValues) => {
    setSavingProfile(true)
    try {
      await updateProfile(values)
      await refreshUser()
      notifySuccess('Profile updated successfully.')
    } catch (error) {
      applyFieldErrors(profileForm, error)
    } finally {
      setSavingProfile(false)
    }
  }

  const handlePasswordSubmit = async (values: PasswordValues) => {
    setSavingPassword(true)
    try {
      await changePassword(values)
      passwordForm.resetFields()
      notifySuccess('Password changed successfully.')
    } catch (error) {
      applyFieldErrors(passwordForm, error)
    } finally {
      setSavingPassword(false)
    }
  }

  if (!profileLoaded || !user) {
    return (
      <section className="mx-auto max-w-7xl px-4 py-10 md:mx-8 xl:px-16">
        <h1 className="mb-6 text-3xl font-bold text-[#08060d]">Profile</h1>
        <Skeleton active paragraph={{ rows: 8 }} />
      </section>
    )
  }

  const initials = user.full_name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? '')
    .join('')

  return (
    <section className="mx-auto max-w px-4 py-10 md:mx-8 xl:px-16">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-[#08060d]">Profile</h1>
        <p className="mt-2 text-gray-600">
          Update your account information and password
        </p>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-4 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-[#1677ff] text-xl font-semibold text-white">
          {initials}
        </div>
        <div className="min-w-0">
          <p className="truncate text-lg font-semibold text-[#08060d] mb-0">
            {user.full_name}
          </p>
          <p className="truncate text-sm text-gray-500">{user.email}</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {level && (
            <Tag color={levelColor(level.level)} className="mr-0">
              {levelLabel(level.level, level.title)}
            </Tag>
          )}
          <Tag color={user.is_mentor ? 'purple' : 'blue'} className="mr-0">
            {user.is_mentor ? 'Mentor' : 'Student'}
          </Tag>
        </div>
      </div>

      <div className="mb-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <TrophyOutlined className="text-lg text-amber-500" />
          <h2 className="text-lg font-semibold text-[#08060d] mb-0">Badge</h2>
        </div>
        <p className="mb-4 text-sm text-gray-500">
          Badges you have collected from the courses you have taken.
        </p>
        <BadgeGrid earnedOnly showCourse />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-[#08060d]">Account Information</h2>
          <p className="mt-1 text-sm text-gray-500">
            Display name and email used to sign in.
          </p>
          <Form
            form={profileForm}
            layout="vertical"
            requiredMark={false}
            onFinish={handleProfileSubmit}
            className="mt-4"
          >
            <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
              <Form.Item
                label="First name"
                name="first_name"
                rules={[{ required: true, message: 'First name is required' }]}
              >
                <Input
                  prefix={<UserOutlined className="text-gray-400" />}
                  placeholder="Budi"
                  autoComplete="given-name"
                />
              </Form.Item>
              <Form.Item
                label="Last name"
                name="last_name"
                rules={[{ required: true, message: 'Last name is required' }]}
              >
                <Input placeholder="Santoso" autoComplete="family-name" />
              </Form.Item>
            </div>
            <Form.Item
              label="Email"
              name="email"
              rules={[
                { required: true, message: 'Email is required' },
                { type: 'email', message: 'Invalid email format' },
              ]}
              extra="Email is also used to sign in."
            >
              <Input
                prefix={<MailOutlined className="text-gray-400" />}
                placeholder="you@example.com"
                autoComplete="email"
              />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={savingProfile}>
              Save Changes
            </Button>
          </Form>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-[#08060d]">Change Password</h2>
          <p className="mt-1 text-sm text-gray-500">
            New password must be at least 8 characters.
          </p>
          <Form
            form={passwordForm}
            layout="vertical"
            requiredMark={false}
            onFinish={handlePasswordSubmit}
            className="mt-4"
          >
            <Form.Item
              label="Old password"
              name="old_password"
              rules={[{ required: true, message: 'Old password is required' }]}
            >
              <Input.Password
                prefix={<LockOutlined className="text-gray-400" />}
                placeholder="••••••••"
                autoComplete="current-password"
              />
            </Form.Item>
            <Form.Item
              label="New password"
              name="new_password"
              hasFeedback
              rules={[
                { required: true, message: 'New password is required' },
                { min: 8, message: 'Minimum 8 characters' },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined className="text-gray-400" />}
                placeholder="••••••••"
                autoComplete="new-password"
              />
            </Form.Item>
            <Form.Item
              label="Confirm new password"
              name="new_password_confirm"
              dependencies={['new_password']}
              hasFeedback
              rules={[
                { required: true, message: 'Password confirmation is required' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('new_password') === value) {
                      return Promise.resolve()
                    }
                    return Promise.reject(new Error('Passwords do not match'))
                  },
                }),
              ]}
            >
              <Input.Password
                prefix={<LockOutlined className="text-gray-400" />}
                placeholder="••••••••"
                autoComplete="new-password"
              />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={savingPassword}>
              Change Password
            </Button>
          </Form>
        </div>
      </div>
    </section>
  )
}
