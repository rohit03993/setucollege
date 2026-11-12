import { useEffect, useState } from "react";
import { api } from "./api.js";

const DEFAULTS = {
  about: "Right College. Right Course. Right Future. Compare fees, NIRF rank, and last year's official JEE and NEET closing ranks.",
};

const ICONS = {
  Instagram: (
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3h10a4 4 0 0 1 4 4v10a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V7a4 4 0 0 1 4-4zm5 4.5A4.5 4.5 0 1 0 16.5 12 4.5 4.5 0 0 0 12 7.5zm5.25-.95a1.05 1.05 0 1 0 1.05 1.05 1.05 1.05 0 0 0-1.05-1.05zM12 9.2A2.8 2.8 0 1 1 9.2 12 2.8 2.8 0 0 1 12 9.2z" /></svg>
  ),
  YouTube: (
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M23 12.2s0-3.2-.4-4.6a3 3 0 0 0-2.1-2.1C18.9 5 12 5 12 5s-6.9 0-8.5.5a3 3 0 0 0-2.1 2.1C1 9 1 12.2 1 12.2s0 3.2.4 4.6a3 3 0 0 0 2.1 2.1C5.1 19.4 12 19.4 12 19.4s6.9 0 8.5-.5a3 3 0 0 0 2.1-2.1c.4-1.4.4-4.6.4-4.6zM9.8 15.5v-6.6l6.2 3.3z" /></svg>
  ),
  Facebook: (
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 9h3V6h-3c-2.2 0-4 1.8-4 4v2H8v3h2v7h3v-7h2.6l.4-3H13v-2c0-.6.4-1 1-1z" /></svg>
  ),
  LinkedIn: (
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 3a2 2 0 1 0 .01 4.01A2 2 0 0 0 5 3zM3 8h4v13H3zm6 0h3.8v1.8h.1A4.2 4.2 0 0 1 17 8c4 0 4.7 2.6 4.7 6v7H18v-6.2c0-1.5 0-3.4-2.1-3.4s-2.4 1.6-2.4 3.3V21H9z" /></svg>
  ),
};

export default function Footer() {
  const [site, setSite] = useState(DEFAULTS);

  useEffect(() => {
    api("/site").then(setSite).catch(() => {});
  }, []);

  const contact = [site.email, site.phone, site.whatsapp, site.address].some(Boolean);
  const social = [
    ["Instagram", site.instagram],
    ["YouTube", site.youtube],
    ["Facebook", site.facebook],
    ["LinkedIn", site.linkedin],
  ].filter((item) => item[1]);
  const phoneHref = String(site.phone || "").replace(/[^\d+]/g, "");

  return (
    <footer className="site-foot">
      <div className="wrap">
        <div className="foot-grid">
          <div className="foot-brand">
            <a className="foot-logo" href="/"><img src="/assets/logo.jpg?v=2" alt="Admission Setu" /></a>
            <p>{site.about || DEFAULTS.about}</p>
          </div>
          <nav aria-label="Explore">
            <h2>Explore</h2>
            <a href="/">Home</a>
            <a href="/browse">Colleges</a>
            <a href="/chances">Predict</a>
          </nav>
          <nav aria-label="Exams">
            <h2>Exams</h2>
            <a href="/chances?exam=JEE%20Main">JEE Main</a>
            <a href="/chances?exam=JEE%20Advanced">JEE Advanced</a>
            <a href="/chances?exam=NEET">NEET</a>
          </nav>
          {contact ? (
            <div className="foot-contact">
              <h2>Contact</h2>
              {site.email ? <a href={`mailto:${site.email}`}>{site.email}</a> : null}
              {site.phone ? <a href={`tel:${phoneHref}`}>{site.phone}</a> : null}
              {site.whatsapp ? <a href={`https://wa.me/91${site.whatsapp}`} target="_blank" rel="noopener">WhatsApp</a> : null}
              {site.address ? <p>{site.address}</p> : null}
            </div>
          ) : null}
        </div>
        <div className="foot-base">
          <div className="foot-legal">
            <p>© 2026 Admission Setu</p>
          </div>
          {social.length ? (
            <div className="foot-social">
              {social.map(([label, href]) => (
                <a key={label} href={href} aria-label={label} target="_blank" rel="noopener">{ICONS[label]}</a>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </footer>
  );
}
