import { useEffect, useState } from "react";
import { api, clearStudent, digitsOnly, lettersOf, loadStudent, saveStudent } from "./api.js";

export default function Account({ onClose, onStudent }) {
  const existing = loadStudent();
  const [step, setStep] = useState(existing ? "home" : "mobile");
  const [mobile, setMobile] = useState("");
  const [otp, setOtp] = useState("");
  const [name, setName] = useState("");
  const [consent, setConsent] = useState(false);
  const [student, setStudent] = useState(existing);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!existing) return;
    api(`/students/${encodeURIComponent(existing.id)}`)
      .then((data) => {
        const next = { id: data.id, name: data.name, mobile: data.mobile, role: data.role || "student", consent_at: data.consent_at || "" };
        saveStudent(next);
        setStudent(next);
        onStudent(next);
      })
      .catch(() => {});
  }, []);

  async function sendCode(event) {
    event.preventDefault();
    setError("");
    const number = digitsOnly(mobile);
    if (!/^[6-9]\d{9}$/.test(number)) {
      setError("Enter a 10-digit Indian mobile number.");
      return;
    }
    setBusy(true);
    try {
      await api("/auth/otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mobile: number })
      });
      setMobile(number);
      setStep("otp");
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  async function login(event) {
    event.preventDefault();
    setError("");
    if (step === "name" && !consent) {
      setError("Tick the box to agree before we save your name and mobile number.");
      return;
    }
    setBusy(true);
    try {
      const result = await api("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mobile,
          otp,
          name: step === "name" ? name : "",
          consent: step === "name"
        })
      });
      if (result.needs_name) {
        setStep("name");
        return;
      }
      saveStudent(result);
      setStudent(result);
      onStudent(result);
      setStep("home");
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    await api("/auth/logout", { method: "POST" }).catch(() => {});
    clearStudent();
    onStudent(null);
  }

  async function withdraw() {
    if (!student) return;
    setError("");
    try {
      await api(`/students/${encodeURIComponent(student.id)}`, { method: "DELETE" });
      await logout();
    } catch (failure) {
      setError(failure.message);
    }
  }

  const titles = { mobile: "Log in", otp: "WhatsApp code", name: "Create your ID", home: "Your account" };
  const role = student?.role === "admin" || student?.role === "staff" ? student.role : "student";
  const roleLabel = { admin: "Admin", staff: "Staff", student: "Student" }[role];

  return (
    <div className="account-dialog" role="dialog" aria-modal="true" aria-labelledby="account-title">
      <form onSubmit={step === "mobile" ? sendCode : login}>
        <div className="student-head">
          <h2 id="account-title">{titles[step]}</h2>
          <button className="student-close" type="button" onClick={onClose}>Close</button>
        </div>
        {step === "mobile" ? (
          <>
            <p>Enter your mobile number. A new number asks for your name and consent after the code.</p>
            <label className="field"><span>Mobile number</span>
            <input value={mobile} inputMode="numeric" maxLength={10} placeholder="10-digit Indian number" onChange={(event) => setMobile(digitsOnly(event.target.value))} />
          </label>
          </>
        ) : null}
        {step === "otp" ? (
          <>
            <p>Enter the 4-digit WhatsApp code. Until WhatsApp is connected, the code is 1234.</p>
            <label className="field"><span>Code</span>
              <input value={otp} inputMode="numeric" maxLength={4} onChange={(event) => setOtp(event.target.value.replace(/\D/g, "").slice(0, 4))} />
            </label>
          </>
        ) : null}
        {step === "name" ? (
          <>
            <p>This number is new. Your name and mobile number create your account.</p>
            <label className="field"><span>Name</span>
              <input value={name} maxLength={80} onChange={(event) => setName(event.target.value)} />
            </label>
            <label className="consent-row">
              <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
              <span>I agree that Admission Setu can save my name and mobile number with this prediction in my account. I can withdraw this from my account.</span>
            </label>
          </>
        ) : null}
        {step === "home" && student ? (
          <>
            <div className="who">
              <span className="who-mark">{lettersOf(student.name) || "AS"}</span>
              <div>
                <p className="account-id"><strong>{student.name}</strong><span className="role-badge" data-role={role}>{roleLabel}</span></p>
                <p className="who-id">{student.id}</p>
              </div>
            </div>
            {role === "admin" ? <a className="button" href="/admin">Open college desk</a> : null}
            <section className="account-block">
              <h3>This account</h3>
              <p>Mobile <strong>{student.mobile || ""}</strong></p>
              <p>Consent was saved when this account was created.</p>
              <button className="ghost" type="button" onClick={withdraw}>Withdraw consent</button>
            </section>
            <button className="ghost" type="button" onClick={logout}>Log out</button>
          </>
        ) : null}
        {error ? <p className="status" role="alert">{error}</p> : null}
        {step !== "home" ? <button className="button" type="submit" disabled={busy || (step === "name" && !consent)}>{step === "mobile" ? "Send code" : step === "otp" ? "Log in" : "Create my ID"}</button> : null}
      </form>
    </div>
  );
}
