const { useState } = React;

/* ---------- reusable blank input ---------- */
function F({ w, ...rest }) {
  return <input className="fld" style={w ? { width: w } : null} {...rest} />;
}

/* =========================================================
   FORM 1 — Shift Supervisor Paperwork Checklist
   ========================================================= */
function ChecklistRow({ box, level, children, cbState, cbSet, id }) {
  return (
    <tr>
      {box ? (
        <td className="box">
          <input type="checkbox" className="cbx" checked={!!cbState[id]}
                 onChange={e => cbSet(id, e.target.checked)} />
        </td>
      ) : (
        <td className="spacer-box"></td>
      )}
      <td className={level === 1 ? "lvl1" : level === 2 ? "lvl2" : ""}>{children}</td>
    </tr>
  );
}

function ShiftChecklist() {
  const [cb, setCbState] = useState({});
  const set = (id, v) => setCbState(s => ({ ...s, [id]: v }));
  const [opt, setOpt] = useState({});
  const o = (id, v) => setOpt(s => ({ ...s, [id]: v }));

  const rows = [
    { box: true, l: 0, t: <span>Video Footage( Label Example: <b><u>NCU</u></b> -2023-12-001)</span> },
    { box: false, l: 1, t: "CD checked and video footage present" },
    { box: false, l: 1, t: "2 copies for use of force and PREA" },
    { box: true, l: 0, t: "Incident Checklist" },
    { box: true, l: 0, t: "Incident review cover sheet if PREA, use of force, or Investigation" },
    { box: true, l: 0, t: "Supervisors cover letter if needed (Use of Force, Prea, and serious incidents ect.)" },
    { box: true, l: 0, t: "005/409 Form" },
    { box: true, l: 0, t: "Major Disciplinary Form" },
    { box: true, l: 0, t: "Photograph Include front, back, top and palms of hands,  for each inmate. Individual placard or header for each inmate" },
    { box: true, l: 0, t: "401 Confiscation completed" },
    { box: false, l: 1, t: "copy of 401 added to packet" },
    { box: false, l: 1, t: "Picture of contraband" },
    { box: false, l: 1, t: "picture of drugs on scale with weight visible" },
    { box: false, l: 1, t: "Drugs, large amount tobbacco ect. Chain of custody" },
    { box: false, l: 2, t: "copy of chain of custody with packet" },
    { box: false, l: 2, t: "documents to accompany Evidence into Wardens locker, origional 401, original chain of custody, Copy of 005" },
    { box: true, l: 0, t: "Weapon- Chain of Custody" },
    { box: true, l: 0, t: "Witness Statements from each inmate" },
    { box: true, l: 0, t: "Enemy Alert copy with packet" },
    { box: false, l: 1, t: "Enemy Alert Recommendation hard copies in warden box" },
    { box: true, l: 0, t: (
      <span className="inline-opt">Medical Report
        <span className="inline-cbx"><input type="checkbox" className="cbx" checked={!!opt.medRefused} onChange={e=>o('medRefused',e.target.checked)} /></span> Refused
      </span>) },
    { box: true, l: 0, t: (
      <span className="inline-opt">Inmate Drug test Form
        <span className="inline-cbx"><input type="checkbox" className="cbx" checked={!!opt.drugRefused} onChange={e=>o('drugRefused',e.target.checked)} /></span> Refused
        <span className="inline-cbx"><input type="checkbox" className="cbx" checked={!!opt.drugHosp} onChange={e=>o('drugHosp',e.target.checked)} /></span> transported to hospital due to medical emergency
      </span>) },
    { box: true, l: 0, t: "Job Changed in e-Omis if not field Utility or Hall Porter" },
    { box: false, l: 1, t: "Classification e-mailed about job changes" },
    { box: true, l: 0, t: "24 hour RH placement form generated and included in packet if inmate kept in isolation" },
    { box: false, l: 1, t: "Copy of 24 hr placement placed in wardens box" },
    { box: true, l: 0, t: "Emergency Hospital Gate Pass if treated outside the unit. Normally  will be a separate incident from the original." },
    { box: false, l: 1, t: "copy of emergency gate pass with packet" },
    { box: false, l: 1, t: "put inmate description, age, class custody level ect. in body of 005 and incident summary" },
    { box: false, l: 1, t: "Gate pass notification information Sheet completed" },
    { box: false, l: 1, t: "Duty warden, chaplain, and classification notified if admitted to the Hospital" },
    { box: false, l: 1, t: "ADC radio room notified if inmate admitted to hospital" },
    { box: true, l: 0, t: "Start time and date and end time and date of investigation must be clear." },
    { box: false, l: 1, t: "violation time / date on any disciplinary during an investigation will be the ending time/ date of the investigation." },
    { box: true, l: 0, t: "Make sure times match on front/ Back 005's, disciplinary, and incident log" },
    { box: true, l: 0, t: "Check Name Spelling and ADC# are correct on front/ Back 005's, disciplinary, Disciplinary Charge line, and incident log" },
    { box: true, l: 0, t: "All pages of the incident packet have the incident number written on them." },
    { box: true, l: 0, t: "Incident Geo coded in e-Omis" },
  ];

  return (
    <div className="chk">
      <p className="title">Shift Supervisor Paperwork Checklist</p>
      <p className="subtitle">Incident Packet review checklist</p>
      <table>
        <tbody>
          {rows.map((r, i) => (
            <ChecklistRow key={i} box={r.box} level={r.l} id={"r" + i} cbState={cb} cbSet={set}>
              {r.t}
            </ChecklistRow>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* =========================================================
   FORM 2 — PREA Incident After Action Review (cover)
   ========================================================= */
function PreaCover() {
  return (
    <div className="cover">
      <div className="frame">
        <div className="big">
          <div className="l1">PREA</div>
          <div className="l2">Incident</div>
          <div className="l3">After Action Review</div>
          <div className="l4">Incident Tracking #&nbsp; <F w="180px" /></div>
        </div>
        <div className="meta">
          <div className="row"><span>Inmate(s):</span> <F w="300px" /></div>
          <div className="row"><span>Staff:</span> <F w="300px" /></div>
        </div>
      </div>
    </div>
  );
}

/* =========================================================
   FORM 3 — Abuse of the PREA Hotline Warning
   ========================================================= */
function HotlineWarning() {
  return (
    <div className="doc warn">
      <div style={{ display: "flex", justifyContent: "center" }}>
        <div className="seal">ADC<br/>SEAL</div>
      </div>
      <h2>ABUSE OF THE PREA HOTLINE WARNING</h2>
      <p className="sub">Arkansas Department of Corrections</p>

      <table className="idtable">
        <tbody>
          <tr>
            <td style={{ width: "50%" }}>Name: <F w="55%" /></td>
            <td style={{ width: "50%" }}>ADC/PID: <F w="55%" /></td>
          </tr>
          <tr>
            <td>Facility: <F w="55%" /></td>
            <td>Call Date: <F w="55%" /></td>
          </tr>
          <tr>
            <td colSpan={2}>Issuing Staff: <F w="80%" /></td>
          </tr>
        </tbody>
      </table>

      <p style={{ fontWeight: 700, margin: "0 0 4px" }}>Disclaimer:</p>
      <p style={{ marginTop: 0 }}>
        The Arkansas Department of Corrections (DOC) has a zero tolerance towards all forms of sexual
        abuse and sexual harassment. The DOC must provide numerous internal ways for offenders to report
        sexual abuse and sexual harassment. One of the designated ways is the PREA Hotline. The PREA
        Hotline is only to be used for reporting sexual abuse and sexual harassment. Your call was reviewed
        and determined to be abusing the hotline in one or more of the following ways:
      </p>
      <ol>
        <li>Reporting something other than sexual abuse or sexual harassment</li>
        <li>Repeatedly calling regarding the same incident</li>
        <li>Providing false allegations</li>
        <li>Threatening the safety or security of staff</li>
      </ol>
      <p>
        By signing this warning form, you are acknowledging that your actions are considered abusing the
        hotline. If continued, you may receive disciplinary action for abusing the PREA Hotline.
      </p>

      <div className="sigrow">
        <span className="lbl">Staff Signature:</span> <F w="300px" />
        <span className="lbl">Date:</span> <F w="130px" />
      </div>
      <div className="sigrow">
        <span className="lbl">Offender Signature:</span> <F w="285px" />
        <span className="lbl">Date:</span> <F w="130px" />
      </div>
    </div>
  );
}

/* =========================================================
   FORM 4 — Emergency Medical Gate Pass Creation Checklist
   ========================================================= */
function GatePassChecklist() {
  const sub = [
    ["A:", "Issue date", "Todays date"],
    ["B:", "Destination", "Baxter Regional Medical Center or other"],
    ["C:", "Reason for Trip", "Medical Emergency"],
    ["D:", "Escorted by:", "Highest rank on escort team usually Sgt."],
    ["E:", "Projected return time:", "11:59 PM"],
    ["F:", "Pass requested by:", "Highest ranking officer on shift usually Lt. on nights"],
    ["G:", "Prepared By:", "Officer preparing gate Pass"],
    ["H", "Requested Date:", "Todays Date"],
    ["I", "Requested Time:", "Right Now"],
    ["J", "Status: requested", "Do not change anything at this time"],
    ["K", "As of date", "Today"],
    ["L", "Add short descritpion in remarks", "Example- Inmate Bob is going to Baxter Regional due to (list medical reason) per medical staff"],
  ];
  return (
    <div className="gate">
      <p className="title">Emergency Medical Gate Pass Creation Checklist</p>
      <ol className="steps">
        <li>Select inmate</li>
        <li>Go to find in menu and select "Job/ Program assingment"</li>
        <li>Select Blue Date next to newest job entry</li>
        <li>Write Down Job/Program Code from the third line down and section number if available
          <div className="blankline" style={{ display: "block", marginLeft: 0, marginTop: 4 }}>
            Job Code: <F w="150px" />&nbsp;&nbsp;&nbsp;Section: <F w="150px" />
          </div>
        </li>
        <li>Go to find in menu and select "Gate Pass search"</li>
        <li>Type in North Central then select new</li>
        <li>Fill in all the blue asteriks
          <ul className="sub">
            {sub.map((s, i) => (
              <li key={i}>
                <span className="k">{s[0]}</span>
                <span>{s[1]}<div className="star">* {s[2]}</div></span>
              </li>
            ))}
          </ul>
        </li>
        <li>Select the three bars and down arrow next to the green save button in the upper right corner
          <div style={{ paddingLeft: 20 }}>Include work squad</div>
        </li>
        <li>Select job / Program code from step# 4</li>
        <li>Slect clear all from the upper right blue button</li>
        <li>Now select the inmate you want on the gate pass</li>
        <li>Hit the save button</li>
        <li>Change Status from requested to approved and save</li>
        <li>click on the gate pass you just created and write down the Sequence Number
          <div className="blankline" style={{ display: "block", marginLeft: 0, marginTop: 4 }}>
            Sequence #: <F w="170px" />
          </div>
        </li>
        <li>Go to find in menu and select "Main Gate pass"</li>
        <li>Enter location: North Central  Date: Date gate pass was created  Sequence # from Step #14 and Submit</li>
        <li>Wait for form to generate then print it out.</li>
      </ol>
    </div>
  );
}

/* =========================================================
   FORM 5 — Chain of Custody
   ========================================================= */
function ChainOfCustody() {
  const rows = Array.from({ length: 11 });
  return (
    <div className="doc coc">
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <div className="seal" style={{ flex: "0 0 auto" }}>ARKANSAS<br/>DOC</div>
        <div style={{ flex: 1 }}>
          <h2 style={{ marginBottom: 0 }}>ARKANSAS DEPARTMENT OF CORRECTIONS</h2>
          <p className="sub">Division of Correction – Director's Office</p>
          <p className="addr">
            6814 Princeton Pike<br/>
            Pine Bluff, Arkansas 71602<br/>
            Phone: (870) 267-6200 &nbsp;|&nbsp; Fax: (870) 267-6244
          </p>
        </div>
      </div>

      <h3>CHAIN OF CUSTODY</h3>
      <hr style={{ border: "none", borderTop: "1px solid #333" }} />

      <div className="line">
        <span className="lbl">DATE:</span> <F w="110px" />
        <span className="lbl">TIME:</span> <F w="90px" />
        <span className="lbl">DOC EMPLOYEE:</span> <F className="fld grow" />
      </div>
      <div className="line">
        <span className="lbl">DESCRIPTION OF ITEM:</span> <F className="fld grow" />
      </div>
      <div className="line"><F className="fld grow" style={{ width: "100%" }} /></div>
      <div className="line">
        <span className="lbl">LOCATION WHERE ITEM WAS FOUND:</span> <F className="fld grow" />
      </div>
      <div className="line">
        <span className="lbl">VICTIM'S NAME &amp; ADC:</span> <F className="fld grow" />
      </div>
      <div className="line">
        <span className="lbl">SUSPECT NAME &amp; ADC:</span> <F className="fld grow" />
      </div>

      <h3>POST ORDERS</h3>
      <p className="post">
        The officer designated as the evidence custodian will be responsible for the handling, marking, packing and securing of all
        evidence. Any employee that seizes evidence involving a crime will complete a 401 Form describing the property and
        involved personnel. The original chain of custody form will be attached to the physical evidence and a copy will be attached
        to the Incident Report (005). The person seizing the evidence will normally maintain custody of that evidence until it is
        placed in the evidence locker. If it is necessary for more than one person to assume custody of the item seized, then each of
        them will make a notation on the chain of custody record. <b>EVERY PERSON WHO ASSUMES CUSTODY OF ANY
        EVIDENCE MUST FILL OUT a (005) INCIDENT REPORT.</b>
      </p>
      <p className="post">
        Evidence that may be fingerprinted <b>SHALL NOT</b> be placed into a plastic bag or other airtight container. Damp or biological
        evidence <b>SHALL NOT</b> be placed in a plastic bag. Paper folds will be suitable for small amounts of suspected narcotic
        substances, hair, fibers, etc. The paper folds will then be placed into another container such as a paper bag. The evidence
        container will be sealed with some type of evidence fracture tape that will indicate any type of tampering.
      </p>
      <p className="post" style={{ fontStyle: "italic" }}>
        * My signature indicates that I have fully understood the Chain-Of-Custody Post Orders.
      </p>

      <table className="sigtable">
        <thead>
          <tr>
            <th style={{ width: "30%" }}>Signature of Releasing Officer</th>
            <th style={{ width: "30%" }}>Signature of Receiving Officer</th>
            <th style={{ width: "20%" }}>Date</th>
            <th style={{ width: "20%" }}>Time</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((_, i) => (
            <tr key={i}><td></td><td></td><td></td><td></td></tr>
          ))}
        </tbody>
      </table>

      <div className="foot">
        <span>CC:&nbsp; Warden</span>
        <span>CHNOFCUS.DOC&nbsp;&nbsp;&nbsp;REV: 11/17/2021</span>
      </div>
    </div>
  );
}

/* =========================================================
   FORM 6 — PREA Step by Step Checklist (two pages)
   ========================================================= */
function PreaStepChecklist() {
  const [cb, setCbState] = useState({});
  const set = (id, v) => setCbState(s => ({ ...s, [id]: v }));

  const CheckRow = ({ id, children }) => (
    <tr>
      <td className="box">
        <input type="checkbox" className="cbx" checked={!!cb[id]} onChange={e => set(id, e.target.checked)} />
      </td>
      <td>{children}</td>
    </tr>
  );

  const steps = [
    "Received information or observed PREA incident",
    "Separate inmates if not consensual victim goes to Medical aggressor goes to restrictive housing",
    "Never place aggressor, victim, or recent consensual in the shower until after all evidence is collected",
    <span><i><u>Do not house a victim</u></i> in restrictive housing</span>,
    "Initiate PREA Checklist SD-2025-01 pg. 14",
    "Place clean sheet down. Inmate on the sheet; strip all clothing off so that evidence can be collected",
    "Place damp evidence where it can dry then place it in a paper bag.",
    "Contact Duty Warden get approval for gate pass to hospital for rape kit if applicable",
    "Interview each Party separately and privately to get both sides of the story",
  ];

  const emails = [
    ["Thomas Hurst", "Warden"],
    ["Kennie Bolden", "Dept. Warden/ PREA Coordinator"],
    ["Marjorie Hall (MarHall@Wellpath.us)", "Health Services Admin."],
    ["Lisa Downing (ldowning@wellpath.us)", "Health Services"],
    ["Caitlin Williams (DOC) <Cait.Williams@wellpath.us>", "Mental Health"],
    ["Brian Sights (DOC) <Brian.Sights@Doc.arkansas.gov>", "Chaplain / Victim Advocate"],
    ["Breann Cowgill (DOC) <Breann.Cowgill@arkansas.gov>", "Classification"],
    ["E-Mail (see duty roster)", "Internal Affairs on call"],
    ["Haley Trantham (DOC) haley.trantham@arkansas.gov.", "PREA Compliance"],
    [<span>Christina Thrower (Christina.Thrower@Doc.Arkansas.gov)</span>, <span>HIV Coord. <small>(Only In event of penetration)</small></span>],
    [<span>Rand Champion (Rand.Champion@doc.arkansas.gov)</span>, <span>DOC Comm. Dir. <small>If I/M taken offsite</small></span>],
    [<span>Wade Hodge (DOC)&lt;Wade.Hodge@doc.arkansas.gov&gt;</span>, <span>Chief oF Staff <small>(Only In event of penetration)</small></span>],
    ["Aaron A. Rogers", "Chief of Security"],
    ["Christopher Brandon", "Building Captain"],
    ["David Foster", "Building Captain"],
    ["Bruce Sanders", "Field Captain"],
  ];

  const paperwork = [
    "Cover letter from supervisor reviewing the incident packet",
    "Incident Checklist",
    "PREA Check list",
    "Incident Number in the PREA checklist and on every 005",
    "Major disciplinary reports if applicable",
    "Photo of each inmate involved including any marks or bruises",
    "Video of incident if available",
    "Still photos of incident if applicable",
    "Confiscation forms for any evidence",
    "Chain of custody for evidence",
    "Copy of gate pass if inmate sent out for medical",
    "Infirmary reports for both inmates",
    "RH placement for anyone who went to RH",
    "Copy of area security Logs/ Unannounced rounds",
    "Copy of the camera logs for that day",
    "Witness statements from involved parties",
    "Witness statements from other witnesses",
    "Housing area roster for the date of the incident",
    "Drug test for any inmate involved",
    "Offender Separation alert paperwork",
  ];

  const eomis = [
    "Open incident Umbrella",
    "Incident summary should say ongoing investigation.",
    "Generate a separation Alert reccomendation. Short summary of why separated and incident # in the alert.",
    "Do not scan packet in. E-mail it to CSO for Confidential scan into E-Omis",
    "Put inmate names in Inmates Involved",
    "Put officer conducting investigation name in e-Omis",
    "Enter all evidence retained in its box in e-Omis",
  ];

  return (
    <div className="prea">
      <p className="title">PREA Step by Step Checklist</p>

      <table className="preatbl">
        <tbody>
          {steps.map((t, i) => <CheckRow key={i} id={"s" + i}>{t}</CheckRow>)}
        </tbody>
      </table>

      <table className="preatbl emailtbl">
        <tbody>
          <tr><td className="section" colSpan={2}>Email Notification List</td></tr>
          {emails.map((r, i) => (
            <tr key={i}>
              <td className="name">{r[0]}</td>
              <td className="role">{r[1]}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="advocate">Victim Advocate: Taylors House Batesville #870-569-8024&nbsp;&nbsp;&nbsp;24hr hot line</p>

      <table className="preatbl">
        <tbody>
          <tr><td className="section" colSpan={2}>Paperwork Checklist</td></tr>
          {paperwork.map((t, i) => <CheckRow key={i} id={"p" + i}>{t}</CheckRow>)}
        </tbody>
      </table>

      <table className="preatbl">
        <tbody>
          <tr><td className="section" colSpan={2}>E-Omis Do's and Don'ts</td></tr>
          {eomis.map((t, i) => <CheckRow key={i} id={"e" + i}>{t}</CheckRow>)}
        </tbody>
      </table>
    </div>
  );
}

/* =========================================================
   App shell
   ========================================================= */
const FORMS = [
  { id: "checklist", label: "Supervisor Checklist", C: ShiftChecklist },
  { id: "preastep", label: "PREA Step Checklist", C: PreaStepChecklist },
  { id: "cover", label: "PREA Cover", C: PreaCover },
  { id: "hotline", label: "Hotline Warning", C: HotlineWarning },
  { id: "gatepass", label: "Gate Pass Steps", C: GatePassChecklist },
  { id: "coc", label: "Chain of Custody", C: ChainOfCustody },
];

function App() {
  const [active, setActive] = useState("checklist");
  const [printAll, setPrintAll] = useState(false);

  const doPrint = (all) => {
    setPrintAll(all);
    setTimeout(() => window.print(), 60);
  };

  return (
    <div className={printAll ? "print-all" : ""}>
      <div className="toolbar">
        <h1>Incident Packet Forms</h1>
        {FORMS.map(f => (
          <button key={f.id}
                  className={"tab" + (active === f.id ? " active" : "")}
                  onClick={() => setActive(f.id)}>
            {f.label}
          </button>
        ))}
        <span className="spacer"></span>
        <button className="btn secondary" onClick={() => doPrint(false)}>Print / Save this form</button>
        <button className="btn" onClick={() => doPrint(true)}>Print all</button>
      </div>

      <div className="note">Type into the blue underlined blanks and checkboxes, then Print / Save as PDF.</div>

      <div className="stage">
        {printAll
          ? FORMS.map(f => <div key={f.id} className="page"><f.C /></div>)
          : (() => { const cur = FORMS.find(f => f.id === active); return <div className="page"><cur.C /></div>; })()
        }
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
