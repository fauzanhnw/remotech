import { Button, Checkbox, Form, Input, message } from 'antd'
import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { getFieldErrors, getFirstMessage } from '@/api'
import { useAuth } from '@/auth/AuthContext'
import { AuthCard } from '@/components/auth/AuthCard'
import { usePageTitle } from '@/hooks/usePageTitle'

interface LoginValues {
  /** Backend menerima email lewat field `username`. */
  username: string
  password: string
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form] = Form.useForm<LoginValues>()
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  usePageTitle('Login')

  const handleSubmit = async (values: LoginValues) => {
    setSubmitting(true)
    try {
      await login(values.username, values.password)
      // Kembali ke halaman asal (mis. course detail) bila ada, selain itu ke my-courses.
      const from = (location.state as { from?: string } | null)?.from
      navigate(from ?? '/my-courses', { replace: true })
    } catch (error) {
      const fieldErrors = Object.entries(getFieldErrors(error))
      if (fieldErrors.length > 0) {
        form.setFields(
          fieldErrors.map(([name, help]) => ({
            name: name as keyof LoginValues,
            errors: [help],
          })),
        )
      } else {
        message.error(getFirstMessage(error))
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthCard>
      <Form<LoginValues>
        form={form}
        layout="vertical"
        requiredMark={false}
        onFinish={handleSubmit}
      >
        <Form.Item
          label="Email"
          name="username"
          rules={[
            { required: true, message: 'Email is required' },
            { type: 'email', message: 'Invalid email format' },
          ]}
        >
          <Input size="large" placeholder="you@example.com" autoComplete="email" />
        </Form.Item>

        <Form.Item
          label="Password"
          name="password"
          rules={[{ required: true, message: 'Password is required' }]}
        >
          <Input
            size="large"
            type={showPassword ? 'text' : 'password'}
            placeholder="••••••••"
            autoComplete="current-password"
          />
        </Form.Item>

        <div className="mb-6 flex items-center justify-between">
          <Checkbox
            checked={showPassword}
            onChange={(event) => setShowPassword(event.target.checked)}
          >
            Show Password
          </Checkbox>
          <Link
            to="/forgot-password"
            className="text-sm font-medium text-[#1677ff] hover:text-[#0958d9]"
          >
            Forgot Password?
          </Link>
        </div>

        <Button type="primary" htmlType="submit" block size="large" loading={submitting}>
          Login
        </Button>
      </Form>

      <p className="mt-6 text-center text-sm text-gray-700">
        Don&apos;t have an account?{' '}
        <Link to="/register" className="font-medium text-[#1677ff] hover:text-[#0958d9]">
          Register now
        </Link>
      </p>
    </AuthCard>
  )
}
