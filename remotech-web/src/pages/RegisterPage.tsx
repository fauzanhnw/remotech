import { Alert, Button, Form, Input } from 'antd'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { getFieldErrors, notifyError, register as registerUser } from '@/api'
import { AuthCard } from '@/components/auth/AuthCard'
import { usePageTitle } from '@/hooks/usePageTitle'

interface RegisterValues {
  full_name: string
  email: string
}

/**
 * POST /register/ — backend hanya menerima nama + email, lalu mengirimkan
 * link set-password ke email tersebut (halaman set-password disediakan Django).
 */
export function RegisterPage() {
  const [form] = Form.useForm<RegisterValues>()
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  usePageTitle('Register')

  const handleSubmit = async (values: RegisterValues) => {
    setSubmitting(true)
    try {
      await registerUser(values)
      setDone(true)
    } catch (error) {
      const fieldErrors = Object.entries(getFieldErrors(error))
      if (fieldErrors.length > 0) {
        form.setFields(
          fieldErrors.map(([name, help]) => ({
            name: name as keyof RegisterValues,
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
          message="Registration successful"
          description="We have sent an email to set your password. Once it is done, please sign in."
        />
        <p className="mt-6 text-center text-sm text-gray-700">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-[#1677ff] hover:text-[#0958d9]">
            Login
          </Link>
        </p>
      </AuthCard>
    )
  }

  return (
    <AuthCard>
      <Form<RegisterValues>
        form={form}
        layout="vertical"
        requiredMark={false}
        onFinish={handleSubmit}
      >
        <Form.Item
          label="Full Name"
          name="full_name"
          rules={[{ required: true, message: 'Full name is required' }]}
        >
          <Input size="large" placeholder="Budi Santoso" autoComplete="name" />
        </Form.Item>

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
          Register
        </Button>
      </Form>

      <p className="mt-6 text-center text-sm text-gray-700">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-[#1677ff] hover:text-[#0958d9]">
          Login
        </Link>
      </p>
    </AuthCard>
  )
}
