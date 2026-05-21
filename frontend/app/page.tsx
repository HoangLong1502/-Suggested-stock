import DashboardHome from '../components/dashboard/DashboardHome';

/** Trang tải ngay; dữ liệu giá/% qua client (không chặn SSR ~60–75s). */
export default function Home() {
  return <DashboardHome />;
}
