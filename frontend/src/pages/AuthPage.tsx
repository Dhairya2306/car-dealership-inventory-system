import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ArrowRight, CarFront, Check } from "lucide-react";
import { useAuth } from "../auth/AuthProvider";
import { apiRequest, messageOf } from "../lib/api";
import { validateCredentials } from "../lib/validation";
import { Brand } from "../components/Brand";
import { ErrorMessage } from "../components/Feedback";

export function AuthPage({ register = false }: { register?: boolean }) {
  const { user, signIn, notice } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState(false);
  if (user) return <Navigate to="/inventory" replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    const invalid = validateCredentials(
      email,
      password,
      register && !created ? name : undefined,
    );
    if (invalid) {
      setError(invalid);
      return;
    }
    setBusy(true);
    setError("");
    try {
      if (register && !created) {
        await apiRequest("/auth/register", {
          method: "POST",
          body: { name: name.trim(), email: email.trim(), password },
        });
        setCreated(true);
      }
      await signIn(email, password);
      navigate("/inventory", { replace: true });
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <section className="relative flex flex-col overflow-hidden bg-slate-950 p-8 text-white lg:min-h-screen lg:p-14">
        <Brand light />
        <div className="relative z-10 my-auto max-w-lg py-12 lg:py-20">
          <span className="eyebrow text-orange-400">
            A clearer view of your dealership
          </span>
          <h1 className="mt-5 text-4xl font-semibold leading-tight tracking-tight sm:text-6xl">
            Great inventory.
            <br />
            <span className="text-slate-400">Better business.</span>
          </h1>
          <p className="mt-6 max-w-sm text-base leading-7 text-slate-400">
            One workspace to keep your vehicles organized, your stock accurate,
            and your day moving.
          </p>
          <div className="mt-8 flex flex-wrap gap-4 text-xs text-slate-300">
            <span className="flex items-center gap-2">
              <Check size={15} className="text-orange-400" />
              Live inventory
            </span>
            <span className="flex items-center gap-2">
              <Check size={15} className="text-orange-400" />
              Simple stock management
            </span>
          </div>
        </div>
        <CarFront
          className="pointer-events-none absolute -bottom-20 -right-14 hidden size-80 text-slate-800/50 lg:block"
          strokeWidth={0.6}
          aria-hidden="true"
        />
        <p className="text-xs text-slate-500">
          Built for the way your dealership works.
        </p>
      </section>
      <section className="flex items-center justify-center bg-stone-50 px-6 py-12 sm:px-12">
        <div className="w-full max-w-sm">
          <p className="eyebrow text-orange-700">
            {register ? "Get started" : "Your workspace awaits"}
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight">
            {register ? "Create your account" : "Welcome back"}
          </h2>
          <p className="mt-3 text-sm leading-6 text-slate-500">
            {register
              ? "Bring your vehicle inventory into focus."
              : "Sign in to manage your inventory and stock."}
          </p>
          <form onSubmit={submit} noValidate className="mt-8 space-y-5">
            {notice && (
              <p role="status" className="text-sm text-orange-800">
                {notice}
              </p>
            )}
            {created && (
              <p role="status" className="text-sm text-emerald-800">
                Your account is created. Sign in to continue.
              </p>
            )}
            <ErrorMessage message={error} />
            {register && (
              <label className="field-label">
                Name
                <input
                  name="name"
                  autoComplete="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  maxLength={100}
                  disabled={busy || created}
                  placeholder="Your full name"
                />
              </label>
            )}
            <label className="field-label">
              Email address
              <input
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={busy || created}
                placeholder="you@dealership.com"
              />
            </label>
            <label className="field-label">
              Password
              <input
                name="password"
                type="password"
                autoComplete={register ? "new-password" : "current-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={busy}
                maxLength={128}
                aria-describedby={register ? "password-hint" : undefined}
                placeholder={
                  register ? "At least 12 characters" : "Enter your password"
                }
              />
            </label>
            {register && (
              <p id="password-hint" className="text-xs text-slate-500">
                Use 12–128 characters. A longer phrase works well.
              </p>
            )}
            <button className="btn-primary w-full" disabled={busy}>
              {busy
                ? "Please wait…"
                : register && !created
                  ? "Create account"
                  : "Sign in"}
              <ArrowRight size={17} aria-hidden="true" />
            </button>
          </form>
          <p className="mt-7 text-center text-sm text-slate-500">
            {register ? "Already have an account?" : "New to Motordesk?"}{" "}
            <Link
              className="font-semibold text-orange-700 hover:underline"
              to={register ? "/login" : "/register"}
            >
              {register ? "Sign in" : "Create an account"}
            </Link>
          </p>
        </div>
      </section>
    </main>
  );
}
