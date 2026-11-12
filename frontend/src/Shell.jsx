import { useState } from "react";
import { useLocation } from "react-router-dom";
import Account from "./Account.jsx";
import Footer from "./Footer.jsx";
import { lettersOf, loadStudent } from "./api.js";

function menuLabel(name) {
  const first = String(name || "").trim().split(/\s+/)[0];
  if (!first) return "Log in";
  return first.length > 12 ? `${first.slice(0, 11)}…` : first;
}

export default function Shell({ children }) {
  const location = useLocation();
  const [student, setStudent] = useState(loadStudent);
  const [accountOpen, setAccountOpen] = useState(false);
  const colleges = location.pathname.startsWith("/browse") || location.pathname.startsWith("/college");
  const label = menuLabel(student?.name);

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <a className="brand" href="/">
            <img src="/assets/logo.jpg?v=2" alt="Admission Setu" />
          </a>
          <nav className="desktop-nav" aria-label="Primary">
            <a href="/">Home</a>
            <a href="/browse" aria-current={colleges ? "page" : undefined}>Colleges</a>
            <a href="/chances">Predict</a>
            <button className="account-link" type="button" title={student?.name || "Log in"} onClick={() => setAccountOpen(true)}>
              {student?.name ? <span className="nav-mark" aria-hidden="true">{(lettersOf(student.name) || "AS").slice(0, 2)}</span> : null}
              <span className="nav-name">{label}</span>
            </button>
          </nav>
        </div>
      </header>
      <main className="wrap">{children}</main>
      <Footer />
      <nav className="tabbar" aria-label="Primary">
        <a href="/">Home</a>
        <a href="/browse" aria-current={colleges ? "page" : undefined}>Colleges</a>
        <a href="/chances">Predict</a>
        <button type="button" title={student?.name || "Log in"} onClick={() => setAccountOpen(true)}>
          <span className="nav-name">{label}</span>
        </button>
      </nav>
      {accountOpen ? (
        <Account
          onClose={() => setAccountOpen(false)}
          onStudent={(next) => {
            setStudent(next);
            if (!next) setAccountOpen(false);
          }}
        />
      ) : null}
    </>
  );
}
