import { createBrowserRouter } from "react-router-dom";

import { HomePage } from "@/app/pages/HomePage";
import { NotFoundPage } from "@/app/pages/NotFoundPage";
import { LoginPlaceholderPage } from "@/features/auth/pages/LoginPlaceholderPage";
import { AdminDashboardPage } from "@/features/admin/pages/AdminDashboardPage";
import { MemberDashboardPage } from "@/features/member/pages/MemberDashboardPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <HomePage />,
  },
  {
    path: "/login",
    element: <LoginPlaceholderPage />,
  },
  {
    path: "/member",
    element: <MemberDashboardPage />,
  },
  {
    path: "/admin",
    element: <AdminDashboardPage />,
  },
  {
    path: "*",
    element: <NotFoundPage />,
  },
]);
