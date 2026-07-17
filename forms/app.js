function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const {
  useState
} = React;

/* ---------- reusable blank input ---------- */
function F({
  w,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("input", _extends({
    className: "fld",
    style: w ? {
      width: w
    } : null
  }, rest));
}

/* =========================================================
   FORM 1 — Shift Supervisor Paperwork Checklist
   ========================================================= */
function ChecklistRow({
  box,
  level,
  children,
  cbState,
  cbSet,
  id
}) {
  return /*#__PURE__*/React.createElement("tr", null, box ? /*#__PURE__*/React.createElement("td", {
    className: "box"
  }, /*#__PURE__*/React.createElement("input", {
    type: "checkbox",
    className: "cbx",
    checked: !!cbState[id],
    onChange: e => cbSet(id, e.target.checked)
  })) : /*#__PURE__*/React.createElement("td", {
    className: "spacer-box"
  }), /*#__PURE__*/React.createElement("td", {
    className: level === 1 ? "lvl1" : level === 2 ? "lvl2" : ""
  }, children));
}
function ShiftChecklist() {
  const [cb, setCbState] = useState({});
  const set = (id, v) => setCbState(s => ({
    ...s,
    [id]: v
  }));
  const [opt, setOpt] = useState({});
  const o = (id, v) => setOpt(s => ({
    ...s,
    [id]: v
  }));
  let n = 0;
  const rows = [{
    box: true,
    l: 0,
    t: /*#__PURE__*/React.createElement("span", null, "Video Footage( Label Example: ", /*#__PURE__*/React.createElement("b", null, /*#__PURE__*/React.createElement("u", null, "NCU")), " -2023-12-001)")
  }, {
    box: false,
    l: 1,
    t: "CD checked and video footage present"
  }, {
    box: false,
    l: 1,
    t: "2 copies for use of force and PREA"
  }, {
    box: true,
    l: 0,
    t: "Incident Checklist"
  }, {
    box: true,
    l: 0,
    t: "Incident review cover sheet if PREA, use of force, or Investigation"
  }, {
    box: true,
    l: 0,
    t: "Supervisors cover letter if needed (Use of Force, Prea, and serious incidents ect.)"
  }, {
    box: true,
    l: 0,
    t: "005/409 Form"
  }, {
    box: true,
    l: 0,
    t: "Major Disciplinary Form"
  }, {
    box: true,
    l: 0,
    t: "Photograph Include front, back, top and palms of hands,  for each inmate. Individual placard or header for each inmate"
  }, {
    box: true,
    l: 0,
    t: "401 Confiscation completed"
  }, {
    box: false,
    l: 1,
    t: "copy of 401 added to packet"
  }, {
    box: false,
    l: 1,
    t: "Picture of contraband"
  }, {
    box: false,
    l: 1,
    t: "picture of drugs on scale with weight visible"
  }, {
    box: false,
    l: 1,
    t: "Drugs, large amount tobbacco ect. Chain of custody"
  }, {
    box: false,
    l: 2,
    t: "copy of chain of custody with packet"
  }, {
    box: false,
    l: 2,
    t: "documents to accompany Evidence into Wardens locker, origional 401, original chain of custody, Copy of 005"
  }, {
    box: true,
    l: 0,
    t: "Weapon- Chain of Custody"
  }, {
    box: true,
    l: 0,
    t: "Witness Statements from each inmate"
  }, {
    box: true,
    l: 0,
    t: "Enemy Alert copy with packet"
  }, {
    box: false,
    l: 1,
    t: "Enemy Alert Recommendation hard copies in warden box"
  }, {
    box: true,
    l: 0,
    t: /*#__PURE__*/React.createElement("span", {
      className: "inline-opt"
    }, "Medical Report", /*#__PURE__*/React.createElement("span", {
      className: "inline-cbx"
    }, /*#__PURE__*/React.createElement("input", {
      type: "checkbox",
      className: "cbx",
      checked: !!opt.medRefused,
      onChange: e => o('medRefused', e.target.checked)
    })), " Refused")
  }, {
    box: true,
    l: 0,
    t: /*#__PURE__*/React.createElement("span", {
      className: "inline-opt"
    }, "Inmate Drug test Form", /*#__PURE__*/React.createElement("span", {
      className: "inline-cbx"
    }, /*#__PURE__*/React.createElement("input", {
      type: "checkbox",
      className: "cbx",
      checked: !!opt.drugRefused,
      onChange: e => o('drugRefused', e.target.checked)
    })), " Refused", /*#__PURE__*/React.createElement("span", {
      className: "inline-cbx"
    }, /*#__PURE__*/React.createElement("input", {
      type: "checkbox",
      className: "cbx",
      checked: !!opt.drugHosp,
      onChange: e => o('drugHosp', e.target.checked)
    })), " transported to hospital due to medical emergency")
  }, {
    box: true,
    l: 0,
    t: "Job Changed in e-Omis if not field Utility or Hall Porter"
  }, {
    box: false,
    l: 1,
    t: "Classification e-mailed about job changes"
  }, {
    box: true,
    l: 0,
    t: "24 hour RH placement form generated and included in packet if inmate kept in isolation"
  }, {
    box: false,
    l: 1,
    t: "Copy of 24 hr placement placed in wardens box"
  }, {
    box: true,
    l: 0,
    t: "Emergency Hospital Gate Pass if treated outside the unit. Normally  will be a separate incident from the original."
  }, {
    box: false,
    l: 1,
    t: "copy of emergency gate pass with packet"
  }, {
    box: false,
    l: 1,
    t: "put inmate description, age, class custody level ect. in body of 005 and incident summary"
  }, {
    box: false,
    l: 1,
    t: "Gate pass notification information Sheet completed"
  }, {
    box: false,
    l: 1,
    t: "Duty warden, chaplain, and classification notified if admitted to the Hospital"
  }, {
    box: false,
    l: 1,
    t: "ADC radio room notified if inmate admitted to hospital"
  }, {
    box: true,
    l: 0,
    t: "Start time and date and end time and date of investigation must be clear."
  }, {
    box: false,
    l: 1,
    t: "violation time / date on any disciplinary during an investigation will be the ending time/ date of the investigation."
  }, {
    box: true,
    l: 0,
    t: "Make sure times match on front/ Back 005's, disciplinary, and incident log"
  }, {
    box: true,
    l: 0,
    t: "Check Name Spelling and ADC# are correct on front/ Back 005's, disciplinary, Disciplinary Charge line, and incident log"
  }, {
    box: true,
    l: 0,
    t: "All pages of the incident packet have the incident number written on them."
  }, {
    box: true,
    l: 0,
    t: "Incident Geo coded in e-Omis"
  }];
  return /*#__PURE__*/React.createElement("div", {
    className: "chk"
  }, /*#__PURE__*/React.createElement("p", {
    className: "title"
  }, "Shift Supervisor Paperwork Checklist"), /*#__PURE__*/React.createElement("p", {
    className: "subtitle"
  }, "Incident Packet review checklist"), /*#__PURE__*/React.createElement("table", null, /*#__PURE__*/React.createElement("tbody", null, rows.map((r, i) => /*#__PURE__*/React.createElement(ChecklistRow, {
    key: i,
    box: r.box,
    level: r.l,
    id: "r" + i,
    cbState: cb,
    cbSet: set
  }, r.t)))));
}

/* =========================================================
   FORM 2 — PREA Incident After Action Review (cover)
   ========================================================= */
function PreaCover() {
  return /*#__PURE__*/React.createElement("div", {
    className: "cover"
  }, /*#__PURE__*/React.createElement("div", {
    className: "frame"
  }, /*#__PURE__*/React.createElement("div", {
    className: "big"
  }, /*#__PURE__*/React.createElement("div", {
    className: "l1"
  }, "PREA"), /*#__PURE__*/React.createElement("div", {
    className: "l2"
  }, "Incident"), /*#__PURE__*/React.createElement("div", {
    className: "l3"
  }, "After Action Review"), /*#__PURE__*/React.createElement("div", {
    className: "l4"
  }, "Incident Tracking #\xA0 ", /*#__PURE__*/React.createElement(F, {
    w: "180px"
  }))), /*#__PURE__*/React.createElement("div", {
    className: "meta"
  }, /*#__PURE__*/React.createElement("div", {
    className: "row"
  }, /*#__PURE__*/React.createElement("span", null, "Inmate(s):"), " ", /*#__PURE__*/React.createElement(F, {
    w: "300px"
  })), /*#__PURE__*/React.createElement("div", {
    className: "row"
  }, /*#__PURE__*/React.createElement("span", null, "Staff:"), " ", /*#__PURE__*/React.createElement(F, {
    w: "300px"
  })))));
}

/* =========================================================
   FORM 3 — Abuse of the PREA Hotline Warning
   ========================================================= */
function HotlineWarning() {
  return /*#__PURE__*/React.createElement("div", {
    className: "doc warn"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      justifyContent: "center"
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "seal"
  }, "ADC", /*#__PURE__*/React.createElement("br", null), "SEAL")), /*#__PURE__*/React.createElement("h2", null, "ABUSE OF THE PREA HOTLINE WARNING"), /*#__PURE__*/React.createElement("p", {
    className: "sub"
  }, "Arkansas Department of Corrections"), /*#__PURE__*/React.createElement("table", {
    className: "idtable"
  }, /*#__PURE__*/React.createElement("tbody", null, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("td", {
    style: {
      width: "50%"
    }
  }, "Name: ", /*#__PURE__*/React.createElement(F, {
    w: "55%"
  })), /*#__PURE__*/React.createElement("td", {
    style: {
      width: "50%"
    }
  }, "ADC/PID: ", /*#__PURE__*/React.createElement(F, {
    w: "55%"
  }))), /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("td", null, "Facility: ", /*#__PURE__*/React.createElement(F, {
    w: "55%"
  })), /*#__PURE__*/React.createElement("td", null, "Call Date: ", /*#__PURE__*/React.createElement(F, {
    w: "55%"
  }))), /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("td", {
    colSpan: 2
  }, "Issuing Staff: ", /*#__PURE__*/React.createElement(F, {
    w: "80%"
  }))))), /*#__PURE__*/React.createElement("p", {
    style: {
      fontWeight: 700,
      margin: "0 0 4px"
    }
  }, "Disclaimer:"), /*#__PURE__*/React.createElement("p", {
    style: {
      marginTop: 0
    }
  }, "The Arkansas Department of Corrections (DOC) has a zero tolerance towards all forms of sexual abuse and sexual harassment. The DOC must provide numerous internal ways for offenders to report sexual abuse and sexual harassment. One of the designated ways is the PREA Hotline. The PREA Hotline is only to be used for reporting sexual abuse and sexual harassment. Your call was reviewed and determined to be abusing the hotline in one or more of the following ways:"), /*#__PURE__*/React.createElement("ol", null, /*#__PURE__*/React.createElement("li", null, "Reporting something other than sexual abuse or sexual harassment"), /*#__PURE__*/React.createElement("li", null, "Repeatedly calling regarding the same incident"), /*#__PURE__*/React.createElement("li", null, "Providing false allegations"), /*#__PURE__*/React.createElement("li", null, "Threatening the safety or security of staff")), /*#__PURE__*/React.createElement("p", null, "By signing this warning form, you are acknowledging that your actions are considered abusing the hotline. If continued, you may receive disciplinary action for abusing the PREA Hotline."), /*#__PURE__*/React.createElement("div", {
    className: "sigrow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "lbl"
  }, "Staff Signature:"), " ", /*#__PURE__*/React.createElement(F, {
    w: "300px"
  }), /*#__PURE__*/React.createElement("span", {
    className: "lbl"
  }, "Date:"), " ", /*#__PURE__*/React.createElement(F, {
    w: "130px"
  })), /*#__PURE__*/React.createElement("div", {
    className: "sigrow"
  }, /*#__PURE__*/React.createElement("span", {
    className: "lbl"
  }, "Offender Signature:"), " ", /*#__PURE__*/React.createElement(F, {
    w: "285px"
  }), /*#__PURE__*/React.createElement("span", {
    className: "lbl"
  }, "Date:"), " ", /*#__PURE__*/React.createElement(F, {
    w: "130px"
  })));
}

/* =========================================================
   FORM 4 — Emergency Medical Gate Pass Creation Checklist
   ========================================================= */
function GatePassChecklist() {
  const sub = [["A:", "Issue date", "Todays date"], ["B:", "Destination", "Baxter Regional Medical Center or other"], ["C:", "Reason for Trip", "Medical Emergency"], ["D:", "Escorted by:", "Highest rank on escort team usually Sgt."], ["E:", "Projected return time:", "11:59 PM"], ["F:", "Pass requested by:", "Highest ranking officer on shift usually Lt. on nights"], ["G:", "Prepared By:", "Officer preparing gate Pass"], ["H", "Requested Date:", "Todays Date"], ["I", "Requested Time:", "Right Now"], ["J", "Status: requested", "Do not change anything at this time"], ["K", "As of date", "Today"], ["L", "Add short descritpion in remarks", "Example- Inmate Bob is going to Baxter Regional due to (list medical reason) per medical staff"]];
  return /*#__PURE__*/React.createElement("div", {
    className: "gate"
  }, /*#__PURE__*/React.createElement("p", {
    className: "title"
  }, "Emergency Medical Gate Pass Creation Checklist"), /*#__PURE__*/React.createElement("ol", {
    className: "steps"
  }, /*#__PURE__*/React.createElement("li", null, "Select inmate"), /*#__PURE__*/React.createElement("li", null, "Go to find in menu and select \"Job/ Program assingment\""), /*#__PURE__*/React.createElement("li", null, "Select Blue Date next to newest job entry"), /*#__PURE__*/React.createElement("li", null, "Write Down Job/Program Code from the third line down and section number if available", /*#__PURE__*/React.createElement("div", {
    className: "blankline",
    style: {
      display: "block",
      marginLeft: 0,
      marginTop: 4
    }
  }, "Job Code: ", /*#__PURE__*/React.createElement(F, {
    w: "150px"
  }), "\xA0\xA0\xA0Section: ", /*#__PURE__*/React.createElement(F, {
    w: "150px"
  }))), /*#__PURE__*/React.createElement("li", null, "Go to find in menu and select \"Gate Pass search\""), /*#__PURE__*/React.createElement("li", null, "Type in North Central then select new"), /*#__PURE__*/React.createElement("li", null, "Fill in all the blue asteriks", /*#__PURE__*/React.createElement("ul", {
    className: "sub"
  }, sub.map((s, i) => /*#__PURE__*/React.createElement("li", {
    key: i
  }, /*#__PURE__*/React.createElement("span", {
    className: "k"
  }, s[0]), /*#__PURE__*/React.createElement("span", null, s[1], /*#__PURE__*/React.createElement("div", {
    className: "star"
  }, "* ", s[2])))))), /*#__PURE__*/React.createElement("li", null, "Select the three bars and down arrow next to the green save button in the upper right corner", /*#__PURE__*/React.createElement("div", {
    style: {
      paddingLeft: 20
    }
  }, "Include work squad")), /*#__PURE__*/React.createElement("li", null, "Select job / Program code from step# 4"), /*#__PURE__*/React.createElement("li", null, "Slect clear all from the upper right blue button"), /*#__PURE__*/React.createElement("li", null, "Now select the inmate you want on the gate pass"), /*#__PURE__*/React.createElement("li", null, "Hit the save button"), /*#__PURE__*/React.createElement("li", null, "Change Status from requested to approved and save"), /*#__PURE__*/React.createElement("li", null, "click on the gate pass you just created and write down the Sequence Number", /*#__PURE__*/React.createElement("div", {
    className: "blankline",
    style: {
      display: "block",
      marginLeft: 0,
      marginTop: 4
    }
  }, "Sequence #: ", /*#__PURE__*/React.createElement(F, {
    w: "170px"
  }))), /*#__PURE__*/React.createElement("li", null, "Go to find in menu and select \"Main Gate pass\""), /*#__PURE__*/React.createElement("li", null, "Enter location: North Central  Date: Date gate pass was created  Sequence # from Step #14 and Submit"), /*#__PURE__*/React.createElement("li", null, "Wait for form to generate then print it out.")));
}

/* =========================================================
   FORM 5 — Chain of Custody
   ========================================================= */
function ChainOfCustody() {
  const rows = Array.from({
    length: 11
  });
  return /*#__PURE__*/React.createElement("div", {
    className: "doc coc"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 14
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "seal",
    style: {
      flex: "0 0 auto"
    }
  }, "ARKANSAS", /*#__PURE__*/React.createElement("br", null), "DOC"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("h2", {
    style: {
      marginBottom: 0
    }
  }, "ARKANSAS DEPARTMENT OF CORRECTIONS"), /*#__PURE__*/React.createElement("p", {
    className: "sub"
  }, "Division of Correction \u2013 Director's Office"), /*#__PURE__*/React.createElement("p", {
    className: "addr"
  }, "6814 Princeton Pike", /*#__PURE__*/React.createElement("br", null), "Pine Bluff, Arkansas 71602", /*#__PURE__*/React.createElement("br", null), "Phone: (870) 267-6200 \xA0|\xA0 Fax: (870) 267-6244"))), /*#__PURE__*/React.createElement("h3", null, "CHAIN OF CUSTODY"), /*#__PURE__*/React.createElement("hr", {
    style: {
      border: "none",
      borderTop: "1px solid #333"
    }
  }), /*#__PURE__*/React.createElement("div", {
    className: "line"
  }, /*#__PURE__*/React.createElement("span", {
    className: "lbl"
  }, "DATE:"), " ", /*#__PURE__*/React.createElement(F, {
    w: "110px"
  }), /*#__PURE__*/React.createElement("span", {
    className: "lbl"
  }, "TIME:"), " ", /*#__PURE__*/React.createElement(F, {
    w: "90px"
  }), /*#__PURE__*/React.createElement("span", {
    className: "lbl"
  }, "DOC EMPLOYEE:"), " ", /*#__PURE__*/React.createElement(F, {
    className: "fld grow"
  })), /*#__PURE__*/React.createElement("div", {
    className: "line"
  }, /*#__PURE__*/React.createElement("span", {
    className: "lbl"
  }, "DESCRIPTION OF ITEM:"), " ", /*#__PURE__*/React.createElement(F, {
    className: "fld grow"
  })), /*#__PURE__*/React.createElement("div", {
    className: "line"
  }, /*#__PURE__*/React.createElement(F, {
    className: "fld grow",
    style: {
      width: "100%"
    }
  })), /*#__PURE__*/React.createElement("div", {
    className: "line"
  }, /*#__PURE__*/React.createElement("span", {
    className: "lbl"
  }, "LOCATION WHERE ITEM WAS FOUND:"), " ", /*#__PURE__*/React.createElement(F, {
    className: "fld grow"
  })), /*#__PURE__*/React.createElement("div", {
    className: "line"
  }, /*#__PURE__*/React.createElement("span", {
    className: "lbl"
  }, "VICTIM'S NAME & ADC:"), " ", /*#__PURE__*/React.createElement(F, {
    className: "fld grow"
  })), /*#__PURE__*/React.createElement("div", {
    className: "line"
  }, /*#__PURE__*/React.createElement("span", {
    className: "lbl"
  }, "SUSPECT NAME & ADC:"), " ", /*#__PURE__*/React.createElement(F, {
    className: "fld grow"
  })), /*#__PURE__*/React.createElement("h3", null, "POST ORDERS"), /*#__PURE__*/React.createElement("p", {
    className: "post"
  }, "The officer designated as the evidence custodian will be responsible for the handling, marking, packing and securing of all evidence. Any employee that seizes evidence involving a crime will complete a 401 Form describing the property and involved personnel. The original chain of custody form will be attached to the physical evidence and a copy will be attached to the Incident Report (005). The person seizing the evidence will normally maintain custody of that evidence until it is placed in the evidence locker. If it is necessary for more than one person to assume custody of the item seized, then each of them will make a notation on the chain of custody record. ", /*#__PURE__*/React.createElement("b", null, "EVERY PERSON WHO ASSUMES CUSTODY OF ANY EVIDENCE MUST FILL OUT a (005) INCIDENT REPORT.")), /*#__PURE__*/React.createElement("p", {
    className: "post"
  }, "Evidence that may be fingerprinted ", /*#__PURE__*/React.createElement("b", null, "SHALL NOT"), " be placed into a plastic bag or other airtight container. Damp or biological evidence ", /*#__PURE__*/React.createElement("b", null, "SHALL NOT"), " be placed in a plastic bag. Paper folds will be suitable for small amounts of suspected narcotic substances, hair, fibers, etc. The paper folds will then be placed into another container such as a paper bag. The evidence container will be sealed with some type of evidence fracture tape that will indicate any type of tampering."), /*#__PURE__*/React.createElement("p", {
    className: "post",
    style: {
      fontStyle: "italic"
    }
  }, "* My signature indicates that I have fully understood the Chain-Of-Custody Post Orders."), /*#__PURE__*/React.createElement("table", {
    className: "sigtable"
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", {
    style: {
      width: "30%"
    }
  }, "Signature of Releasing Officer"), /*#__PURE__*/React.createElement("th", {
    style: {
      width: "30%"
    }
  }, "Signature of Receiving Officer"), /*#__PURE__*/React.createElement("th", {
    style: {
      width: "20%"
    }
  }, "Date"), /*#__PURE__*/React.createElement("th", {
    style: {
      width: "20%"
    }
  }, "Time"))), /*#__PURE__*/React.createElement("tbody", null, rows.map((_, i) => /*#__PURE__*/React.createElement("tr", {
    key: i
  }, /*#__PURE__*/React.createElement("td", null), /*#__PURE__*/React.createElement("td", null), /*#__PURE__*/React.createElement("td", null), /*#__PURE__*/React.createElement("td", null))))), /*#__PURE__*/React.createElement("div", {
    className: "foot"
  }, /*#__PURE__*/React.createElement("span", null, "CC:\xA0 Warden"), /*#__PURE__*/React.createElement("span", null, "CHNOFCUS.DOC\xA0\xA0\xA0REV: 11/17/2021")));
}

/* =========================================================
   App shell
   ========================================================= */
const FORMS = [{
  id: "checklist",
  label: "Supervisor Checklist",
  C: ShiftChecklist
}, {
  id: "cover",
  label: "PREA Cover",
  C: PreaCover
}, {
  id: "hotline",
  label: "Hotline Warning",
  C: HotlineWarning
}, {
  id: "gatepass",
  label: "Gate Pass Steps",
  C: GatePassChecklist
}, {
  id: "coc",
  label: "Chain of Custody",
  C: ChainOfCustody
}];
function App() {
  const [active, setActive] = useState("checklist");
  const [printAll, setPrintAll] = useState(false);
  const doPrint = all => {
    setPrintAll(all);
    setTimeout(() => window.print(), 60);
  };
  return /*#__PURE__*/React.createElement("div", {
    className: printAll ? "print-all" : ""
  }, /*#__PURE__*/React.createElement("div", {
    className: "toolbar"
  }, /*#__PURE__*/React.createElement("h1", null, "Incident Packet Forms"), FORMS.map(f => /*#__PURE__*/React.createElement("button", {
    key: f.id,
    className: "tab" + (active === f.id ? " active" : ""),
    onClick: () => setActive(f.id)
  }, f.label)), /*#__PURE__*/React.createElement("span", {
    className: "spacer"
  }), /*#__PURE__*/React.createElement("button", {
    className: "btn secondary",
    onClick: () => doPrint(false)
  }, "Print / Save this form"), /*#__PURE__*/React.createElement("button", {
    className: "btn",
    onClick: () => doPrint(true)
  }, "Print all")), /*#__PURE__*/React.createElement("div", {
    className: "note"
  }, "Type into the blue underlined blanks and checkboxes, then Print / Save as PDF."), /*#__PURE__*/React.createElement("div", {
    className: "stage"
  }, printAll ? FORMS.map(f => /*#__PURE__*/React.createElement("div", {
    key: f.id,
    className: "page"
  }, /*#__PURE__*/React.createElement(f.C, null))) : (() => {
    const cur = FORMS.find(f => f.id === active);
    return /*#__PURE__*/React.createElement("div", {
      className: "page"
    }, /*#__PURE__*/React.createElement(cur.C, null));
  })()));
}
ReactDOM.createRoot(document.getElementById("root")).render(/*#__PURE__*/React.createElement(App, null));