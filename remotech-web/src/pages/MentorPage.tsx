import { MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons'
import { Button, Layout, Menu } from 'antd'
import { useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'

import { mentorMenuItems } from './mentor/mentorMenu'

const { Sider } = Layout

/** max-width breakpoint antd `md` — dipakai untuk matchMedia awal & backdrop mobile. */
const MOBILE_QUERY = '(max-width: 767.98px)'

function isMobileViewport() {
  return typeof window !== 'undefined' && window.matchMedia(MOBILE_QUERY).matches
}

/**
 * Layout dashboard mentor: sidebar collapsible di kiri (menu Courses &
 * Assignments) + konten halaman (Outlet) di kanan.
 */
export function MentorPage() {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(isMobileViewport)
  const [belowMd, setBelowMd] = useState(isMobileViewport)

  const selected = mentorMenuItems.find((item) => location.pathname.startsWith(item.to))

  const handleMenuClick = () => {
    // Di layar kecil sidebar menutup setelah menu dipilih agar konten terlihat.
    if (belowMd) setCollapsed(true)
  }

  return (
    <Layout className="min-h-full bg-white">
      <Sider
        theme="light"
        collapsible
        trigger={null}
        collapsed={collapsed}
        onCollapse={setCollapsed}
        breakpoint="md"
        onBreakpoint={setBelowMd}
        collapsedWidth={0}
        width={240}
        className="sticky top-16 h-[calc(100vh-4rem)] overflow-y-auto overflow-x-hidden border-r border-gray-200 bg-white max-md:fixed max-md:left-0 max-md:z-40 max-md:shadow-xl"
      >
        <div className="flex h-14 items-center px-5">
          <span className="font-bold text-[#08060d]">Mentor</span>
        </div>

        <Menu
          mode="inline"
          className="border-none"
          selectedKeys={selected ? [selected.key] : []}
          onClick={handleMenuClick}
          items={mentorMenuItems.map((item) => ({
            key: item.key,
            icon: <item.icon />,
            label: (
              <Link to={item.to} className="text-inherit no-underline">
                {item.label}
              </Link>
            ),
          }))}
        />
      </Sider>

      {!collapsed && belowMd && (
        <div
          aria-hidden
          className="fixed top-16 right-0 bottom-0 left-0 z-30 bg-black/40"
          onClick={() => setCollapsed(true)}
        />
      )}

      <Layout className="bg-white">
        <div className="flex h-14 items-center gap-2 border-b border-gray-200 px-4">
          <Button
            type="text"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed((value) => !value)}
          />
          <span className="text-sm font-semibold text-gray-700">
            {selected?.label ?? 'Mentor'}
          </span>
        </div>

        <div className="flex-1">
          <Outlet />
        </div>
      </Layout>
    </Layout>
  )
}
