/* Sample colleges for the layout preview.
   Numbers follow the shape of the saved College For Me and CollegeDekho fields.
   They are here so the pages can be reviewed before the full catalogue is connected. */
window.SETU = [
  {
    slug: "nit-surathkal",
    name: "NIT Surathkal",
    fullName: "National Institute of Technology Karnataka",
    city: "Mangaluru",
    state: "Karnataka",
    ownership: "Government",
    streams: ["Engineering"],
    established: 1960,
    approvals: ["AICTE", "UGC"],
    naac: "A+",
    nirf: { rank: 17, year: 2025, category: "Engineering" },
    feeLabel: "₹1.25L",
    feeNote: "per year",
    avgPackage: "₹17.5L",
    highestPackage: "₹63.3L",
    medianPackage: "₹14.2L",
    placementRate: "80.6%",
    exams: ["JEE Main"],
    hostel: "Yes",
    campusSize: "295 acres",
    website: "https://www.nitk.ac.in",
    phone: "+91 824 247 4000",
    overview:
      "A central government engineering institute in Surathkal, with B.Tech admission through JEE Main and a large residential campus.",
    courses: [
      { name: "B.Tech Computer Science", level: "UG", duration: "4 years", fee: "₹1.25L / year", eligibility: "JEE Main, class 12 with PCM" },
      { name: "B.Tech Electronics and Communication", level: "UG", duration: "4 years", fee: "₹1.25L / year", eligibility: "JEE Main, class 12 with PCM" },
      { name: "B.Tech Mechanical Engineering", level: "UG", duration: "4 years", fee: "₹1.25L / year", eligibility: "JEE Main, class 12 with PCM" },
      { name: "M.Tech Computer Science", level: "PG", duration: "2 years", fee: "₹70,000 / year", eligibility: "GATE" },
      { name: "MBA", level: "PG", duration: "2 years", fee: "₹1.4L / year", eligibility: "CAT" }
    ],
    admission: [
      { label: "Entrance exam", value: "JEE Main, then JoSAA counselling" },
      { label: "Eligibility", value: "Class 12 with Physics, Chemistry, and Mathematics" },
      { label: "Application", value: "Through the national exam portal, not on the college site" }
    ],
    recruiters: ["Microsoft", "Amazon", "Texas Instruments", "Qualcomm", "Oracle", "Tata Steel"],
    facilities: ["Boys hostel", "Girls hostel", "Central library", "Labs", "Sports complex", "Wi-Fi"],
    scholarships: [
      { name: "Tuition fee waiver", detail: "For eligible family-income bands under the institute rules" },
      { name: "Institute merit scholarship", detail: "Awarded from academic performance after joining" }
    ],
    cutoffs: [
      { course: "B.Tech Computer Science", exam: "JEE Main", closing: "Closing rank in the JoSAA round" },
      { course: "B.Tech Electronics", exam: "JEE Main", closing: "Closing rank in the JoSAA round" },
      { course: "B.Tech Mechanical", exam: "JEE Main", closing: "Closing rank in the JoSAA round" }
    ],
    faqs: [
      { q: "Does the campus have a hostel?", a: "Yes. Hostel facility is listed for this college." },
      { q: "Which exam is required for B.Tech?", a: "JEE Main, followed by JoSAA seat allotment." }
    ],
    shape: "Detailed record: separate course, fee, scholarship, and cutoff rows."
  },
  {
    slug: "iit-madras",
    name: "IIT Madras",
    fullName: "Indian Institute of Technology Madras",
    city: "Chennai",
    state: "Tamil Nadu",
    ownership: "Government",
    streams: ["Engineering"],
    established: 1959,
    approvals: ["AICTE"],
    naac: "",
    nirf: { rank: 1, year: 2025, category: "Engineering" },
    feeLabel: "₹2L–2.31L",
    feeNote: "fee range",
    avgPackage: "₹20L+",
    highestPackage: "",
    medianPackage: "",
    placementRate: "",
    exams: ["JEE Advanced"],
    courseCount: 98,
    hostel: "Yes",
    campusSize: "",
    website: "https://www.iitm.ac.in",
    phone: "",
    overview:
      "The listing groups many B.Tech branches into one fee range. The page keeps that range and the course count, instead of inventing a branch the source did not split out.",
    courses: [
      { name: "B.Tech", level: "UG", duration: "4 years", fee: "₹2,00,000 – ₹2,31,000 / year", eligibility: "JEE Advanced", note: "98 courses listed on the source card" }
    ],
    admission: [
      { label: "Entrance exam", value: "JEE Advanced" },
      { label: "Also listed", value: "JEE Main appears on the source card, with 3 more exams" },
      { label: "Seat allotment", value: "JoSAA / CSAB for B.Tech" }
    ],
    placementRows: [
      { label: "Average package", value: "Shown when the placement table has a figure" },
      { label: "Placement year", value: "Each year in the saved table becomes one row" }
    ],
    recruiters: ["Google", "Microsoft", "Qualcomm", "Texas Instruments"],
    facilities: ["Hostel", "Labs", "Research centres"],
    scholarships: [],
    cutoffs: [],
    faqs: [
      { q: "Why is B.Tech one card?", a: "The saved course page gives a fee range for the program. Branch-wise fees appear only when the source lists them separately." }
    ],
    shape: "Wide listing: one fee range plus the course count from the card."
  },
  {
    slug: "vit-vellore",
    name: "VIT Vellore",
    fullName: "Vellore Institute of Technology",
    city: "Vellore",
    state: "Tamil Nadu",
    ownership: "Private",
    streams: ["Engineering"],
    established: 1984,
    approvals: ["AICTE", "UGC"],
    naac: "A++",
    nirf: { rank: 11, year: 2025, category: "Engineering" },
    feeLabel: "₹1.98L",
    feeNote: "per year",
    avgPackage: "₹9.5L",
    highestPackage: "₹88L",
    medianPackage: "",
    placementRate: "",
    exams: ["VITEEE"],
    hostel: "Yes",
    campusSize: "",
    website: "https://vit.ac.in",
    phone: "",
    overview: "A private deemed university. B.Tech admission is through its own entrance exam, VITEEE.",
    courses: [
      { name: "B.Tech Computer Science", level: "UG", duration: "4 years", fee: "₹1.98L / year", eligibility: "VITEEE" },
      { name: "B.Tech Electronics", level: "UG", duration: "4 years", fee: "₹1.76L / year", eligibility: "VITEEE" },
      { name: "M.Tech", level: "PG", duration: "2 years", fee: "₹1.2L / year", eligibility: "GATE or VIT entrance" }
    ],
    admission: [
      { label: "Entrance exam", value: "VITEEE" },
      { label: "Eligibility", value: "Class 12 with Physics, Chemistry, and Mathematics" }
    ],
    recruiters: ["Microsoft", "Amazon", "Deloitte", "Cisco"],
    facilities: ["Hostel", "Labs", "Sports"],
    scholarships: [{ name: "VITEEE rank scholarship", detail: "Fee reduction by entrance rank band" }],
    cutoffs: [],
    faqs: [],
    shape: "Private college: own exam, fee per course, and a scholarship band."
  },
  {
    slug: "aiims-new-delhi",
    name: "AIIMS New Delhi",
    fullName: "All India Institute of Medical Sciences",
    city: "New Delhi",
    state: "Delhi",
    ownership: "Government",
    streams: ["Medical"],
    established: 1956,
    approvals: ["NMC"],
    naac: "",
    nirf: { rank: 1, year: 2025, category: "Medical" },
    feeLabel: "₹1,628",
    feeNote: "per year",
    avgPackage: "",
    highestPackage: "",
    medianPackage: "",
    placementRate: "",
    exams: ["NEET UG"],
    hostel: "Yes",
    campusSize: "",
    website: "https://www.aiims.edu",
    phone: "",
    overview: "A government medical institute. The page leads with the exam and the fee, and leaves the package row hidden because this record has no placement figure.",
    courses: [
      { name: "MBBS", level: "UG", duration: "5.5 years", fee: "₹1,628 / year", eligibility: "NEET UG" },
      { name: "MD", level: "PG", duration: "3 years", fee: "As notified", eligibility: "INI-CET" }
    ],
    admission: [
      { label: "Entrance exam", value: "NEET UG for MBBS" },
      { label: "Counselling", value: "Medical Counselling Committee" }
    ],
    recruiters: [],
    facilities: ["Hospital", "Hostel", "Library"],
    scholarships: [],
    cutoffs: [{ course: "MBBS", exam: "NEET UG", closing: "All India closing rank" }],
    faqs: [{ q: "Is there a placement package?", a: "No package is stored for this college, so that block is hidden." }],
    shape: "Medical record: exam and fee first. Package stays hidden when it is empty."
  },
  {
    slug: "sibm-pune",
    name: "SIBM Pune",
    fullName: "Symbiosis Institute of Business Management",
    city: "Pune",
    state: "Maharashtra",
    ownership: "Private",
    streams: ["Management"],
    established: 1978,
    approvals: ["AICTE"],
    naac: "",
    nirf: { rank: 13, year: 2025, category: "Management" },
    feeLabel: "₹13.5L",
    feeNote: "per year",
    avgPackage: "₹28L",
    highestPackage: "₹49L",
    medianPackage: "",
    placementRate: "",
    exams: ["SNAP"],
    hostel: "Yes",
    campusSize: "",
    website: "https://www.sibm.edu",
    phone: "",
    overview: "A management institute. The same page layout fits a two-year MBA: fee, package, rank, and entrance exam.",
    courses: [
      { name: "MBA", level: "PG", duration: "2 years", fee: "₹13.5L / year", eligibility: "SNAP, then GE-PI" }
    ],
    admission: [
      { label: "Entrance exam", value: "SNAP" },
      { label: "Next step", value: "Group exercise and personal interview" },
      { label: "Eligibility", value: "A completed bachelor degree" }
    ],
    recruiters: ["Deloitte", "Accenture", "ICICI Bank", "Asian Paints"],
    facilities: ["Hostel", "Library"],
    scholarships: [{ name: "Merit scholarship", detail: "Awarded on the SNAP score and the selection round" }],
    cutoffs: [],
    faqs: [],
    shape: "Management record: one course, a high fee, and the entrance exam in the top row."
  }
];
