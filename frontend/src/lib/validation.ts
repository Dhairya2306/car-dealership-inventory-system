export function validateCredentials(
  email: string,
  password: string,
  name?: string,
): string | null {
  if (name !== undefined && (!name.trim() || name.trim().length > 100))
    return "Enter your name (1–100 characters).";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()))
    return "Enter a valid email address.";
  if (password.length < (name === undefined ? 1 : 12))
    return name === undefined
      ? "Enter your password."
      : "Use at least 12 characters for your password.";
  if (password.length > 128)
    return "Passwords must be 128 characters or fewer.";
  return null;
}

export function validPrice(value: string, allowZero = false): boolean {
  return (
    /^\d{1,10}(\.\d{1,2})?$/.test(value) &&
    (allowZero ? Number(value) >= 0 : Number(value) > 0)
  );
}
export function validQuantity(value: string, allowZero = true): boolean {
  return (
    /^\d+$/.test(value) &&
    Number(value) <= 2147483647 &&
    Number(value) >= (allowZero ? 0 : 1)
  );
}
export function priceLabel(value: string): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: import.meta.env.VITE_CURRENCY || "INR",
    maximumFractionDigits: 2,
  }).format(Number(value));
}
