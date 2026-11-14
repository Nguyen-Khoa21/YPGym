import { useNavigate } from "react-router-dom";

import { MemberShell } from "@/components/layout/MemberShell";
import { routePaths } from "@/app/routes";
import { OnboardingForm } from "./OnboardingForm";

export function OnboardingPage() {
  const navigate = useNavigate();
  return (
    <MemberShell>
      <div className="mx-auto max-w-2xl">
        <p className="page-kicker">Welcome to YPGym</p>
        <h1 className="page-title">A few quick questions.</h1>
        <p className="page-description">
          It takes about a minute. You can skip now and answer later from your profile.
        </p>
        <div className="mt-7">
          <OnboardingForm
            showSkip
            onDone={() => navigate(routePaths.memberDashboard, { replace: true })}
          />
        </div>
      </div>
    </MemberShell>
  );
}
