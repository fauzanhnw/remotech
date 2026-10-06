import { Alert, Button, Form, Input } from 'antd'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { forgotPassword, getFieldErrors, notifyError } from '@/api'
import { AuthCard } from '@/components/auth/AuthCard'
import { usePageTitle } from '@/hooks/usePageTitle'

interface ForgotPasswordValues {
  email: string
}

/** POST /forgot-password/ — selalu 200 meski email tidak terdaftar. */
export function ForgotPasswordPage() {
  const [form] = Form.useForm<ForgotPasswordValues>()
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  usePageTitle('Forgot Password')

  const handleSubmit = async (values: ForgotPasswordValues) => {
    setSubmitting(true)
    try {
      await forgotPassword(values)
      setDone(true)
    } catch (error) {
      const fieldErrors = Object.entries(getFieldErrors(error))
      if (fieldErrors.length > 0) {
        form.setFields(
          fieldErrors.map(([name, help]) => ({
            name: name as keyof ForgotPasswordValues,
            errors: [help],
          })),
        )
      } else {
        notifyError(error)
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (done) {
    return (
      <AuthCard>
        <Alert
          type="success"
          showIcon
          message="Email sent"
          description="If your email is registered, a reset link will be sent within a few minutes."
        />
        <p className="mt-6 text-center text-sm text-gray-700">
          <Link to="/login" className="font-medium text-[#1677ff] hover:text-[#0958d9]">
            Back to Login
          </Link>
        </p>
      </AuthCard>
    )
  }

  return (
    <AuthCard>
      <p className="mb-6 text-sm text-gray-600">
        Enter your account email and we will send you a link to reset your password.
      </p>

      <Form<ForgotPasswordValues>
        form={form}
        layout="vertical"
        requiredMark={false}
        onFinish={handleSubmit}
      >
        <Form.Item
          label="Email"
          name="email"
          rules={[
            { required: true, message: 'Email is required' },
            { type: 'email', message: 'Invalid email format' },
          ]}
        >
          <Input size="large" placeholder="you@example.com" autoComplete="email" />
        </Form.Item>

        <Button type="primary" htmlType="submit" block size="large" loading={submitting}>
          Send Reset Link
        </Button>
      </Form>

      <p className="mt-6 text-center text-sm text-gray-700">
        Remember your password?{' '}
        <Link to="/login" className="font-medium text-[#1677ff] hover:text-[#0958d9]">
          Login
        </Link>
      </p>
    </AuthCard>
  )
}
