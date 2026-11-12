import { useEffect, useState } from "react";
import { api, lettersOf, num, packageText, place, shownFee } from "./api.js";

const STREAMS = [
  ["", "All"],
  ["Engineering", "Engineering"],
  ["Medical", "Medical"],
  ["Management", "Management"]
];

function CardLogo({ college }) {
  const [failed, setFailed] = useState(false);
  const letters = lettersOf(college.name) || "•";
  if (college.logo && !failed) {
    return <img className="card-logo" src={college.logo} alt="" loading="lazy" decoding="async" onError={() => setFailed(true)} />;
  }
  return <span className="card-logo initials-logo">{letters}</span>;
}

function Card({ college }) {
  const [photoFailed, setPhotoFailed] = useState(false);
  const fee = shownFee(college.fee_label);
  const highest = packageText(college);
  const where = [place(college), college.ownership].filter(Boolean).join(" · ");
  const streams = (college.streams || []).filter(Boolean).slice(0, 2);
  return (
    <a className="directory-card" href={`/college/${encodeURIComponent(college.slug)}`}>
      <span className="directory-cover">
        {college.image && !photoFailed ? (
          <img src={college.image} alt="" loading="lazy" decoding="async" onError={() => setPhotoFailed(true)} />
        ) : null}
        {college.nirf_rank ? <span className="rank-badge">NIRF #{num(college.nirf_rank)}</span> : null}
      </span>
      <span className="directory-body">
        <span className="card-title">
          <CardLogo college={college} />
          <span>
            <h3>{college.name}</h3>
            <p className="place">{where}</p>
          </span>
        </span>
        {fee || highest ? (
          <span className="directory-facts">
            {fee ? <span><small>Yearly fee</small>{fee}</span> : null}
            {highest ? <span><small>Highest</small>{highest}</span> : null}
          </span>
        ) : null}
        {streams.length ? (
          <span className="card-tags">{streams.map((stream) => <span key={stream}>{stream}</span>)}</span>
        ) : null}
      </span>
    </a>
  );
}

export default function Browse() {
  const params = new URLSearchParams(window.location.search);
  const [q, setQ] = useState(params.get("q") || "");
  const [stream, setStream] = useState(params.get("stream") || "");
  const [sort, setSort] = useState(params.get("sort") || "name");
  const [page, setPage] = useState(Math.max(1, Number(params.get("page") || 1)));
  const [colleges, setColleges] = useState([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState("Loading colleges…");
  const [more, setMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  function writeUrl(next) {
    const query = new URLSearchParams();
    if (next.q) query.set("q", next.q);
    if (next.stream) query.set("stream", next.stream);
    if (next.sort && next.sort !== "name") query.set("sort", next.sort);
    if (next.page > 1) query.set("page", String(next.page));
    const text = query.toString();
    history.pushState({}, "", text ? `/browse?${text}` : "/browse");
  }

  async function load(next, append) {
    if (append) setLoadingMore(true);
    else setStatus("Loading colleges…");
    const query = new URLSearchParams({
      q: next.q,
      stream: next.stream,
      sort: next.sort,
      page: String(next.page),
      page_size: "20"
    });
    try {
      const data = await api(`/colleges?${query}`);
      const pages = Math.max(1, Math.ceil(data.total / data.page_size));
      setColleges((current) => append ? current.concat(data.colleges) : data.colleges);
      setTotal(data.total);
      const shown = Math.min(data.total, data.page * data.page_size);
      setStatus(data.total ? `${num(shown)} of ${num(data.total)} colleges` : "No colleges");
      setMore(Boolean(data.total) && data.page < pages);
    } catch (error) {
      setStatus(error.message);
      setMore(false);
    } finally {
      setLoadingMore(false);
    }
  }

  useEffect(() => {
    const start = {
      q: params.get("q") || "",
      stream: params.get("stream") || "",
      sort: params.get("sort") || "name",
      page: 1
    };
    setQ(start.q);
    setStream(start.stream);
    setSort(start.sort);
    setPage(1);
    load(start, false);
  }, []);

  function apply(next) {
    const state = { q, stream, sort, ...next, page: 1 };
    setQ(state.q);
    setStream(state.stream);
    setSort(state.sort);
    setPage(state.page);
    writeUrl(state);
    load(state, false);
  }

  return (
    <div className="directory">
      <header className="directory-head">
        <p className="eyebrow">Colleges</p>
        <h1>Top colleges in India</h1>
        <p className="lede">NIRF rank, yearly fee, and courses. The first colleges load with the page, and more load only when you ask.</p>
        <form className="search" onSubmit={(event) => { event.preventDefault(); apply({ q: q.trim() }); }}>
          <label className="sr" htmlFor="q">Search colleges</label>
          <input id="q" value={q} onChange={(event) => setQ(event.target.value)} placeholder="Search by college, city, or state" />
          <button className="button" type="submit">Search</button>
        </form>
      </header>
      <div className="directory-layout">
        <aside className="directory-filters" aria-label="Filter colleges">
          <h2>Filter</h2>
          <div className="filter-block">
            <p>Stream</p>
            <div className="chips" role="group" aria-label="Stream">
              {STREAMS.map(([value, label]) => (
                <button
                  className="chip"
                  type="button"
                  key={label}
                  aria-pressed={stream === value}
                  onClick={() => apply({ stream: value })}
                >{label}</button>
              ))}
            </div>
          </div>
          <label className="filter-block" htmlFor="sort">Sort
            <select id="sort" value={sort} onChange={(event) => apply({ sort: event.target.value })}>
              <option value="name">Name</option>
              <option value="nirf">NIRF rank</option>
              <option value="fee">Yearly fee</option>
            </select>
          </label>
        </aside>
        <div>
          <p className="status">{status}</p>
          <div className="list">
            {colleges.map((college) => <Card key={college.slug} college={college} />)}
            {!colleges.length && status !== "Loading colleges…" ? <p className="empty">Nothing matches that search.</p> : null}
          </div>
          {more ? (
            <div className="pager">
              <button
                className="ghost"
                type="button"
                disabled={loadingMore}
                onClick={() => {
                  const next = { q, stream, sort, page: page + 1 };
                  setPage(next.page);
                  writeUrl(next);
                  load(next, true);
                }}
              >{loadingMore ? "Loading more colleges…" : "Show more colleges"}</button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
