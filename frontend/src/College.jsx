import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, lettersOf, num, packageText, place, shownFee } from "./api.js";

function Table({ table }) {
  const columns = table.columns || [];
  return (
    <div className="table-wrap">
      {table.title ? <h3>{table.title}</h3> : null}
      <table>
        {columns.length ? (
          <thead>
            <tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr>
          </thead>
        ) : null}
        <tbody>
          {(table.rows || []).slice(0, 24).map((row, index) => (
            <tr key={index}>{row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function College() {
  const { slug } = useParams();
  const [college, setCollege] = useState(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("");

  useEffect(() => {
    let live = true;
    setCollege(null);
    setError("");
    setTab("");
    const encoded = encodeURIComponent(slug);
    api(`/colleges/${encoded}?view=card`)
      .then((card) => {
        if (!live) return null;
        setCollege(card);
        document.title = `${card.name} — Admission Setu`;
        return api(`/colleges/${encoded}`);
      })
      .then((full) => {
        if (live && full) setCollege(full);
      })
      .catch((failure) => {
        if (live) setError(failure.message);
      });
    return () => {
      live = false;
    };
  }, [slug]);

  if (!college && error) {
    return <p className="status" role="alert">{error}</p>;
  }
  if (!college) {
    return <p className="status">Loading college…</p>;
  }

  const pages = college.pages || {};
  const groups = pages.course_groups || [];
  const cutoff = pages.cutoff?.tables || [];
  const placements = pages.placement?.tables || [];
  const admission = pages.admission?.sections || [];
  const answers = pages.faqs || [];
  const placementText = (pages.placement?.sections || []).map((section) => section.content || "").join(" ");
  const recruiterMatch = placementText.match(/top recruiters include ([^.]+)/i);
  const recruiters = college.recruiters || (recruiterMatch ? recruiterMatch[1] : "");
  const exams = (college.exams || []).filter(Boolean);
  const rating = /^\d/.test(String(college.rating || "").trim()) ? String(college.rating).trim() : "";
  const videoId = /^[\w-]{11}$/.test(college.video_id || "") ? college.video_id : "";
  const tabs = [
    groups.length ? ["courses", "Courses"] : null,
    college.pages ? ["admission", "Admission"] : null,
    cutoff.length ? ["cutoff", "Cutoff"] : null,
    placements.length || recruiters || college.average_package || college.highest_package ? ["placements", "Placements"] : null,
    answers.length ? ["answers", "Answers"] : null
  ].filter(Boolean);
  const current = tabs.some(([id]) => id === tab) ? tab : tabs[0]?.[0] || "";
  const fee = shownFee(college.fee_label);
  const highest = college.highest_package || packageText(college);
  const facts = [
    fee ? ["Yearly fee", fee] : null,
    college.nirf_rank ? ["NIRF", `#${num(college.nirf_rank)}`] : null,
    college.average_package ? ["Average package", college.average_package] : null,
    highest ? ["Highest package", highest] : null,
    college.course_count ? ["Courses", String(college.course_count)] : null
  ].filter(Boolean);
  const site = String(college.website || "");
  const publicSite = /^https?:\/\//i.test(site) && !/collegedekho\.com/i.test(site) ? site : "";
  const phone = String(college.phone || "").trim();
  const phoneHref = phone.replace(/[^\d+]/g, "");
  const where = [place(college), college.ownership, college.established_year ? `Established ${college.established_year}` : ""].filter(Boolean).join(" · ");

  return (
    <>
      <a className="back" href="/browse">All colleges</a>
      <article className="profile">
        <div className="banner">
          {college.image ? <img className="campus" src={college.image} alt="" /> : <div className="initials">{lettersOf(college.name) || "AS"}</div>}
        </div>
        <div className="identity">
          <div className="identity-top">
            {college.logo ? <img className="college-logo" src={college.logo} alt="" /> : <span className="college-logo initials-logo">{lettersOf(college.name) || "AS"}</span>}
            <div>
              <p className="kicker">{where}</p>
              <h1>{college.name}</h1>
              {rating ? <p className="rating-line"><span className="rating-pill">{rating}</span>{college.reviews ? <span>{college.reviews} reviews</span> : null}</p> : null}
            </div>
          </div>
          {college.overview ? <p className="overview">{college.overview}</p> : null}
          <div className="tags">
            {(college.streams || []).map((stream) => <span className="tag" key={stream}>{stream}</span>)}
            {exams.map((exam) => <span className="tag exam" key={exam}>{exam}</span>)}
          </div>
          {facts.length ? (
            <dl className="metrics">
              {facts.map(([label, value]) => (
                <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
              ))}
            </dl>
          ) : null}
          <p className="contact-line">
            {publicSite ? <a className="text-link" href={publicSite} target="_blank" rel="noopener">Website</a> : null}
            {phone && phoneHref ? <a className="text-link" href={`tel:${phoneHref}`}>{phone}</a> : null}
            <a className="button" href="/chances">Check your rank</a>
          </p>
        </div>
      </article>
      {videoId ? (
        <section className="sheet video-card">
          <h2>Campus video</h2>
          <div className="video">
            <iframe
              src={`https://www.youtube.com/embed/${videoId}`}
              title="Campus video"
              loading="lazy"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
        </section>
      ) : null}
      {college.pages ? null : <p className="status">Loading courses, cutoffs, and placements…</p>}
      {tabs.length ? (
        <nav className="section-nav" aria-label="College sections">
          {tabs.map(([id, label]) => (
            <button key={id} type="button" aria-pressed={current === id} onClick={() => setTab(id)}>{label}</button>
          ))}
        </nav>
      ) : null}
      {current === "courses" ? (
        <section className="sheet">
          <h2>Courses and fees</h2>
          <div className="degree-list">
            {groups.map((group) => (
              <article key={group.degree}>
                <h3>{group.degree}</h3>
                {group.fee ? <p>{group.fee}</p> : null}
                <ul>{(group.courses || []).map((course) => <li key={course}>{course}</li>)}</ul>
              </article>
            ))}
          </div>
        </section>
      ) : null}
      {current === "admission" ? (
        <section className="sheet">
          <h2>Admission</h2>
          {admission.length ? admission.map((section) => (
            <div key={section.title}>
              {section.title ? <h3>{section.title}</h3> : null}
              <p>{section.content}</p>
            </div>
          )) : <p className="sheet-note">Check the current admission notice, then use your rank on the predictor.</p>}
          <a className="button" href="/chances">Check your rank</a>
        </section>
      ) : null}
      {current === "cutoff" ? (
        <section className="sheet">
          <h2>Cutoff</h2>
          <p className="sheet-note">A smaller rank is a better rank.</p>
          {cutoff.slice(0, 6).map((table, index) => <Table key={`${table.title || "cutoff"}-${index}`} table={table} />)}
        </section>
      ) : null}
      {current === "placements" ? (
        <section className="sheet">
          <h2>Placements</h2>
          {recruiters ? <p className="recruiters">Recruiters include {recruiters}</p> : null}
          {placements.slice(0, 4).map((table, index) => <Table key={`${table.title || "placement"}-${index}`} table={table} />)}
        </section>
      ) : null}
      {current === "answers" ? (
        <section className="sheet">
          <h2>Answers</h2>
          {answers.map((item) => (
            <details key={item.question}>
              <summary>{item.question}</summary>
              <p>{item.answer}</p>
            </details>
          ))}
        </section>
      ) : null}
    </>
  );
}
