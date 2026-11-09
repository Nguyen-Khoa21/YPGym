/** A member who signed in with a temporary password must set a private one before using the app. */
export function mustChangePassword(user: { must_change_password?: boolean } | null | undefined): boolean {
  return user?.must_change_password === true;
}

export type PasswordChangeInput = { current: string; next: string; confirm: string };

export function validatePasswordChange({ current, next, confirm }: PasswordChangeInput): { current?: string; next?: string; confirm?: string } {
  return {
    ...(!current ? { current: 'Enter the temporary password you were given.' } : {}),
    ...(next.length < 8 ? { next: 'Use at least 8 characters.' } : {}),
    ...(next && next === current ? { next: 'Choose a password different from the temporary one.' } : {}),
    ...(confirm !== next ? { confirm: 'The passwords do not match.' } : {}),
  };
}
