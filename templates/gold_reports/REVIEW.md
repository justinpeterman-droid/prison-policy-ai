# Gold-standard report library — FOR REVIEW

> **All names and ADC numbers below are placeholders.** Every real identity was
> replaced before this file was created; no real PII has ever been written to this
> repository. The same person maps to the same placeholder across all reports, so
> the prose still reads naturally.

**94 reports** recovered from your archive, grouped into **60 incidents**, of which **18 are matched sets** — the same incident written in more than one voice. Those matched sets are the most valuable examples here, because producing exactly that pairing is what the report generator is being asked to do.

---

## How to review this

For each report, you're answering one question: **is this how you would actually file it?**

- ✏️  **Edit the text directly** if the wording is off. Your edit is the ground truth.
- ❌  **Delete any report** that isn't a good example — a bad example teaches bad habits.
- ⭐  **Mark the best one in each category** by adding `<!-- BEST -->` above it. Those get
     weighted most heavily as few-shot examples.

You do **not** need to review all of them. Even 2–3 approved examples per category is
enough to move the generator substantially.

### The tag above each report

Every report has been scored against `STYLE_RULINGS.md` (run
`PYTHONPATH=. python3 scripts/annotate_review.py` to refresh). The tag tells you
whether the *formatting* needs your attention — it says nothing about whether the
report is a good example, which is the part only you can judge.

| Tag | Count | What it means for you |
|---|---|---|
| ✅ **CONFORMS** | 36 | Formatting already matches the rulings. Judge it on content alone. |
| 🔧 **AUTO-FIXABLE** | 43 | Diverges only in ways `repair()` corrects mechanically — ADC# spacing, a rank period, a stray closer. Normalized automatically before use, so judge it on content alone too. |
| ⚠️ **NEEDS YOUR EDIT** | 15 | No code can fix this without changing what the report *says*. 10 are time formats, 4 have medical detail in the narrative, 1 ends with a closer. Fix the text or skip the report. |

**Why the normalizing matters:** your archive is internally inconsistent — 36 reports
write `ADC#135939` with no space, 24 end with a closer that ruling 13 drops. Feeding
those in raw would teach the generator to violate the very rulings the validator now
enforces, so every approved example is passed through `repair()` first.

---

## Inmate Fight / Assault

*5 incident(s), 10 report(s)*

### Inmate Fight / Assault · incident 1 — **matched set**

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 5/9/2023 at approximately 11:40pm inmate Green, Trudrell ADC#135939 approached 10 barracks door and notified staff that he was assaulted. I, Sergeant Daniel Whitfield, escorted inmate Green to the infirmary to be evaluated by medical staff. I started an investigation at 11:40pm and concluded it at 1:00am on 5/10/2023 with the following findings: At approximately 11:38pm Inmate Marcelis, Alder ADC#144608 approached inmate Sansevero, Alder ADC#181509 while he was at the dayroom table and struck him with a closed fist to the back of the head. Then inmate Marcelis started to go up the stairs and went to Inmate Green’s rack then followed him to the stairway and struck Inmate Green in the mouth. Upon questioning inmate Green, he stated he was assaulted by multiple Inmates but could not identify any of them. After reviewing camera footage and getting statements from inmates that were in the area, I was unable to substantiate inmate Green’s allegations. Inmate Marcelis was escorted to restrictive housing and placed in the holding cell. I escorted Inmate Sansevero to the infirmary to be seen by medical staff. Pictures were taken and drug tests were given, yielding negative results on all inmates. An enemy separation alert was generated. Due to the above stated facts I, Sergeant Daniel Whitfield, am charging inmate Marcelis, Alder ADC#144608 with major rule violation 4-8 pending DCR.
```

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space, ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On 5/9/2023 at approximately 11:40pm inmate Green, Trudrell ADC#135939 approached 10 barracks door and notified staff that he was assaulted. Sergeant Daniel Whitfield escorted inmate Green to the infirmary to be evaluated by medical staff. Sgt. Whitfield started an investigation at 11:40pm and concluded it at 1:00am on 5/10/2023 with the following findings: At approximately 11:38pm Inmate Marcelis, Alder ADC#144608 approached inmate Sansevero, Alder ADC#181509 while he was at the dayroom table and struck him with a closed fist to the back of the head. Then inmate Marcelis started to go up the stairs and went to Inmate Green’s rack then followed him to the stairway and struck Inmate Green in the mouth. Upon questioning inmate Green, he stated he was assaulted by multiple Inmates but could not identify any of them. After reviewing camera footage and getting statements from inmates that were in the area, Sgt. Whitfield was unable to substantiate inmate Green’s allegations. Inmate Marcelis was escorted to restrictive housing and placed in the holding cell. Inmate Sansevero was escorted to the infirmary to be seen by medical staff. Pictures were taken and drug tests were given, yielding negative results on all inmates. An enemy separation alert was generated. Disciplinary action taken.
```

**Short summary**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space, ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On 5/9/2023 at approximately 11:38pm inmate Marcelis, Alder ADC#144608 aggressively struck inmate Sansevero, Alder ADC#181509 and inmate Green, Trudrell ADC#135939 with a closed fist. Inmate Marcelis was escorted to restrictive housing pending DCR. Inmate Green was rehoused to 13 barracks. Disciplinary action taken.
```

### Inmate Fight / Assault · incident 2 — **matched set**

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On 1-11-24 at approximately 10:00pm I, Sgt. Daniel Whitfield, received an unauthored inmate request form that stated that a fight occurred in 9 barracks on 1-10-24. I started my investigation on 1-11-24 at approximately 10:00pm by reviewing camera footage, and I observed on 1-10-24 at approximately 4:51pm Inmate Martinez, Rodolfo ADC# 156793 and Inmate Briley, Eddie ADC# 116921 striking each other with closed fist multiple times on the top tier of 9 barracks. Both inmates were called down to the Lt.s Office individually and placed in hand restraints then escorted to Restrictive Housing. Witness statements were collected. On 1-11-24 at approximately 11:30pm I concluded my investigation with the following findings: Inmate Martinez, Rodolfo ADC# 156793 and Inmate Briley, Eddie ADC# 116921 physically assaulted each other in 9 barracks. Photos were taken, and drug tests were conducted yielding negative results. A separation alert was generated. Both inmates were seen by medical staff. Inmate Martinez was rehoused to 13 barracks and Inmate Briley was returned to 9 barracks. Disciplinary action taken.
```

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 1-11-24 at approximately 10:00pm I, Sgt. Daniel Whitfield, received an unauthored inmate request form that stated that a fight occurred in 9 barracks on 1-10-24. I started my investigation on 1-11-24 at approximately 10:00pm by reviewing camera footage, and I observed on 1-10-24 at approximately 4:51pm Inmate Martinez, Rodolfo ADC# 156793 and Inmate Briley, Eddie ADC# 116921 striking each other with closed fist multiple times on the top tier of 9 barracks. Both inmates were called down to the Lt.s Office individually and placed in hand restraints then escorted to Restrictive Housing. Witness statements were collected. On 1-11-24 at approximately 11:30pm I concluded my investigation with the following findings: Inmate Martinez, Rodolfo ADC# 156793 and Inmate Briley, Eddie ADC# 116921 physically assaulted each other in 9 barracks. Photos were taken, and drug tests were conducted yielding negative results. A separation alert was generated. Both inmates were seen by medical staff. Inmate Martinez was rehoused to 13 barracks and Inmate Briley was returned to 9 barracks. Due to the above stated facts I, Sgt. Daniel Whitfield, am charging Inmate Martinez, Rodolfo ADC# 156793 Inmate Briley, Eddie ADC# 116921 with rule violation 4-8. Pending DCR.
```

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On 1-11-24 at approximately 10:00pm Sgt. Daniel Whitfield received an unauthored inmate request form that stated that a fight occurred in 9 barracks on 1-10-24. He started an investigation on 1-11-24 at approximately 10:00pm by reviewing camera footage, and he observed on 1-10-24 at approximately 4:51pm Inmate Martinez, Rodolfo ADC# 156793 and Inmate Briley, Eddie ADC# 116921 striking each other with closed fist multiple times on the top tier of 9 barracks. Both inmates were called down to the Lt.s Office individually and placed in hand restraints then escorted to Restrictive Housing. Witness statements were collected. On 1-11-24 at approximately 11:30pm Sgt. Whitfield concluded his investigation with the following findings: Inmate Martinez, Rodolfo ADC# 156793 and Inmate Briley, Eddie ADC# 116921 physically assaulted each other in 9 barracks. Photos were taken, and drug tests were conducted yielding negative results. A separation alert was generated. Both inmates were seen by medical staff. Inmate Martinez was rehoused to 13 barracks and Inmate Briley was returned to 9 barracks. Disciplinary action taken.
```

### Inmate Fight / Assault · incident 3 — **matched set**

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 5/14/2023 at approximately 9:00pm I, Sergeant Daniel Whitfield, received an unnamed inmate request form that stated Inmate Willard, Alder ADC#166976 physically assaulted Inmate Duncan, David ADC#175776 in 9 barracks on 5/10/2023. I started my investigation at 9:00pm and concluded it at 10:30pm on 5/14/2023 with the following findings: On 5/10/2023 at approximately 9:33pm Inmate Willard approached Inmate Duncan in 9 barracks dayroom and struck him with a closed fist one time to his face, then both inmates separated. Inmate Duncan did not fight back when assaulted by inmate Willard. Inmate Willard was called to center hallway when I placed him in hand restraints and escorted him to restrictive housing and secured him in the holding cell. I received witness statements from both inmates, and an enemy separation alert was generated. Both inmates were seen by medical staff. Pictures were taken and drug tests were given, yielding negative results on both inmates.  I rehoused Inmate Willard to 14 barracks and returned Inmate Duncan to 9 barracks. Due to the above stated facts I, Sergeant Daniel Whitfield, am charging inmate Willard, Alder ADC#166976 with major rule violation 4-8 pending DCR.
```

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space, ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On 5/14/2023 at approximately 9:00pm Sergeant Daniel Whitfield received an unnamed inmate request form that stated Inmate Willard, Alder ADC#166976 physically assaulted Inmate Duncan, David ADC#175776 in 9 barracks on 5/10/2023. He started am investigation at 9:00pm and concluded it at 10:30pm on 5/14/2023 with the following findings: On 5/10/2023 at approximately 9:33pm Inmate Willard approached Inmate Duncan in 9 barracks dayroom and struck him with a closed fist one time to his face, then both inmates separated. Inmate Duncan did not fight back when assaulted by inmate Willard. Inmate Willard was called to center hallway when I placed him in hand restraints and escorted him to restrictive housing and secured him in the holding cell. Witness statements were received from both inmates, and an enemy separation alert was generated. Both inmates were seen by medical staff. Pictures were taken and drug tests were given, yielding negative results on both inmates.  Inmate Willard was rehoused to 14 barracks and Inmate Duncan was returned to 9 barracks. Disciplinary action taken.
```

### Inmate Fight / Assault · incident 4

**Short summary**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space, ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On 5/10/2023 at approximately 9:33pm inmate Willard, Alder ADC#166976 aggressively struck Inmate Duncan, David ADC#175776 with a closed fist. Inmate Duncan did not fight back when assaulted by inmate Willard. Inmate Willard was rehoused to 14 barracks. Disciplinary action taken.
```

### Inmate Fight / Assault · incident 5

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> ⚠️ NEEDS YOUR EDIT — non-standard time format. No code can fix this without changing what the report says.

```text
On 11/23/2023 at approximately 6:30PM Sgt. Marcus Alder was given information about inmate Guillory, Jeremy ADC #122798 potentially falling down the stairs in 9 Barracks. Due to the bruising being consistent with being in a physical altercation, inmate Guillory was placed in hand restraints and escorted to the Infirmary and then to Restrictive Housing under investigation. Sgt. Alder immediately began watching video footage in 9 Barracks to investigate the issue. He concluded his investigation on 11/23/2023 at approximately 7:30PM with the following findings. Inmate Guillory can be seen in a physical altercation with inmate Jones, Sterling ADC #143346 on the top tier of 9 Barracks on 11/22/2023 at approximately 9:04PM. The inmates waited for staff to finish their security rounds in the barracks across the hall and then move on to the next barracks, so staff would not see the altercation. Sgt. Alder then went to 9 Barracks and gave inmate Jones a direct order to exit the barracks and submit to hand restraints, to which he complied. Inmate Jones was escorted to the Infirmary and then to Restrictive Housing. When asked what the reason for the altercation was about, inmate Jones stated that inmate Guillory was calling him racial slurs at the domino table, but he refused to write it in a witness statement. Inmate Guillory wrote in a witness statement that he fell down the stairs two days ago. Digital photos were taken of the inmates and snapshots were downloaded from the barracks cameras. Inmate Jones was sent back to his assigned rack and inmate Guillory was moved to a different barracks and an enemy separation was completed. Disciplinary action was taken.
```

---

## Staff Assault / Insolence / Threats

*6 incident(s), 8 report(s)*

### Staff Assault / Insolence / Threats · incident 1 — **matched set**

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On 1-25-24 at approximately 7:06 pm I, Cpl. Austin Deforest, observed Inmate Oliver, Markus ADC# 181632 walking down South hallway, then he stopped and started talking through the closed door of 13 Barracks to another inmate. I gave Inmate Oliver a direct order to stop talking and continue down the hallway. Inmate Oliver complied to the order but stated in an insolent manner, “Fuck you man, I wasn’t doin nothin. Get off my fuckin back.” I took this insolent statement as a direct threat to the order and operations of the unit. I ordered Inmate Oliver to submit to hand restraint to which he complied. Sgt. Whitfield and I escorted Inmate Oliver to Restrictive Housing without further incident. Inmate Oliver was later returned to his assigned barracks (Barracks 10). Disciplinary action taken.
```

**Short summary**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On 1-25-24 at approximately 7:06 pm Cpl. Austin Deforest observed Inmate Oliver, Markus ADC# 181632 walking down South hallway, then he stopped and started talking through the closed door of 13 Barracks to another inmate. Cpl. Deforest gave Inmate Oliver a direct order to stop talking and continue down the hallway. Inmate Oliver complied to the order but stated in an insolent manner, “Fuck you man, I wasn’t doin nothin. Get off my fuckin back.” Disciplinary action taken.
```

### Staff Assault / Insolence / Threats · incident 2 — **matched set**

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 1-30-24 at approximately 7:50pm I, Cpl. Anthony Vredenburg, was conducting a security check in 12 Barracks when I observed a trash can placed in front of the shower area when Inmate Everett, Jesse ADC# 147410 was taking a shower. I informed Inmate Everett that he could not place the trash can in front of the shower and ordered him to remove it. Inmate Everett refused the order and Inmate Burnett, Grant ADC# 182421 that was in the bathroom area started to question me and stated in an insolent tone, “Fuck no I ain’t doing it!” I ordered Inmate Burnett to step into the hallway when he was finished using the restroom. As I exited the Barracks Inmate Burnett placed trash can lid blocking my view of the bathroom area. I counseled Inmate Burnett in the hallway about placing the trash can lid and returned him to 12 Barracks. Due to the above stated fact I, Cpl. Anthony Vredenburg, am charging Inmate Everett, Jesse ADC# 147410 Burnett, Grant ADC# 182421 with rule violation 11-2, 12-3. Pending DCR.
```

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On 1-30-24 at approximately 7:50pm Cpl. Anthony Vredenburg was conducting a security check in 12 Barracks when he observed a trash can placed in front of the shower area when Inmate Everett, Jesse ADC# 147410 was taking a shower. He informed Inmate Everett that he could not place the trash can in front of the shower and ordered him to remove it. Inmate Everett refused the order and Inmate Burnett, Grant ADC# 182421 that was in the bathroom area started to question Cpl. Vredenburg and stated in an insolent tone, “Fuck no I ain’t doing it!” Inmate Burnett was ordered to step into the hallway when he was finished using the restroom. As Cpl. Vredenburg exited the Barracks Inmate Burnett placed a trash can lid blocking the view of the bathroom area. Disciplinary action taken.
```

### Staff Assault / Insolence / Threats · incident 3

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> ⚠️ NEEDS YOUR EDIT — non-standard time format. No code can fix this without changing what the report says.

```text
At approximately 9:15PM I entered barrack 13 with Sgt. Daniel Whitfield and Cpl. Austin Deforest and observed Inmate Brewer, Jamal ADC# 172575 sitting on his assigned rack #3. I asked him his name and he said “Brewer, why?” I then told him I had seen him on camera with fire ignited. He said, “you are a fucking liar, if you had me on camera, I’d be in the hole right now.” I said you are right, come to the hallway to which he replied, “you can’t keep me, you’ll just have to cut me back out.” I then gave him a direct order to exit the barracks to the hallway to which he complied, but his anger and hostility escalated as he said “you’re a bogus ass Niger! You’re a fucking liar!” Once in the hallway, hand restraints were applied, and he was escorted to Restrictive Housing where he continued to yell obscenities and verbal threats to staff.
```

### Staff Assault / Insolence / Threats · incident 4

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ⚠️ NEEDS YOUR EDIT — non-standard time format. No code can fix this without changing what the report says.

```text
On July 18, 2023 I, Sergeant Daniel Whitfield, was assisting with Minor Disciplinary court in the Lt. office. At approximately 9:52PM Inmate Richardson, Jacob ADC#162481 was called into the office for a minor disciplinary written on him when he became insolent to staff by stating, “Fuck You, Your on some bogus ass bullshit”. Inmate Richardson was placed in hand restraints and escorted to restrictive housing.
```

### Staff Assault / Insolence / Threats · incident 5

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> ⚠️ NEEDS YOUR EDIT — non-standard time format. No code can fix this without changing what the report says.

```text
On 7/29/23 at approximately 11:49AM Cpl. Shane Reyes observed Inmate Bledsoe, Richard #232343 yelling and disrupting 8 Barracks shortly after a fight that occurred while holding additional security in 8 Barracks. Inmate Bledsoe was given several direct orders to sit on his rack and be quiet. Inmate Bledsoe refused by stating in an insolent tone, "Fuck this, guys we can't let this dumbass shit ride!" attempting to incite other inmates to disrupt unit operations. Inmate Bledsoe was given direct orders to exit 8 Barracks to which he complied. Once in the hallway Inmate Bledsoe was given a direct order to submit to hand restraints to which he initially complied. The left hand was restrained to which Inmate Bledsoe started to twist his right hand and tensing his arms, resisting staff. Inmate Bledsoe was given direct orders to stop to which he then pulled his right arm away from staff. Inmate Bledsoe was placed against the wall by Cpl. Foster and Cpl. Reyes (in attempt to regain compliance) where he continued to resist by yelling and pulling away. Inmate Bledsoe was then secured on the floor so that compliance could be regained where he was placed in restraints and then escorted to Restrictive Housing. Photographs were taken, video footage downloaded, and Inmate Bledsoe was later seen by medical. Deputy Warden Underwood approved Behavior Control status to be utilized. Disciplinary action taken.
```

### Staff Assault / Insolence / Threats · incident 6

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 11/6/2023 at approx. 1:00pm I Sgt. Drew Smith was supervising Field Utility 12 inmates raking leaves on the freeline.  At this time, I observed Inmate Burnett, Grant ADC# 182421 out of line not raking his skip of leaves.  I gave Inmate Burnett a direct order to get back into his spot in line and to rake his skip of leaves.  Inmate Burnett then became insolent towards me stating "Man I am getting my leaves leave me the fuck alone!"  I attempted to counsel with the inmate but he became increasingly agitated and insolent.  I then gave Inmate Burnett a direct order to drop his tool and get on his knees and radioed for my supervisor who then came and picked up the inmate and escorted him back to sally port.  Due to the above stated facts I Sgt. Drew Smith am charging Inmate Burnett, Grant ADC# 182421 with rule violations 02-13, 12-3, and 11-1, pending DCR.
```

---

## Use of Force (chemical agents, taser, forced restraint)

*3 incident(s), 6 report(s)*

### Use of Force (chemical agents, taser, forced restraint) · incident 1 — **matched set**

**First person (005 narrative)**  <sub>`christie_report_.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space, ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On December 30th, 2021 I, Sergeant Daniel Whitfield, was working my assigned post as Restrictive Housing Security Supervisor. At approximately 7:15pm I was walking down the south hallway in restrictive housing when I observed Corporal Marcus Alder, Corporal Trevor Kemp, Captain Denise Fairbanks standing in the outer doorway of cell 21. When approaching cell 21 I noticed that the two inmates, inmate Cranston Mitchell ADC#220686 and inmate Kessler Win ADC#223076, had been exposed to OC chemical agents. Cpl. Alder and Cpl. Kemp applied hand restraints to both inmates and escorted inmate Kessler to the back shower #3. Cpl. Grant Holloway and I escorted inmate Kessler to the front shower #1 for decontamination and to be see by medical. End of report.
```

**First person (005 narrative)**  <sub>`christie_report_.docx`</sub>

> 🔧 AUTO-FIXABLE — ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On December 30th, 2021 I, Corporal Grant Holloway, was working my assigned post as Restrictive Housing Security Officer. At approximately 7:15pm I was inventorying property in restrictive housing when Sergeant Daniel Whitfield instructed me to follow him to cell 21. Cpl. Marcus Alder and Cpl. Trevor Kemp applied hand restraints on inmate Cranston Mitchell #220686 and inmate Kessler Win #223076. Sgt. Whitfield and I escorted inmate Kessler to shower #1. I then returned to my normal duties. End of report.
```

**Third person / supervisor**  <sub>`christie_report_.docx`</sub>

> 🔧 AUTO-FIXABLE — ends with a statement closer. Normalized automatically before use; judge it on content.

```text
At approx. 7:15pm Cpl. Z. Alder and myself were performing Supply and Mail call at Cell #19 when Cpt. K. Fairbanks called me to cell #21, which was housed by inmate M. Cranston ADC #220686 and W. Kessler ADC #223076. I then observed Inmate Cranston stroking his exposed penis in a back-and-forth motion in front of inmate Kessler who was on the top rack. At this time, we gave inmate Cranston a direct order to stop his actions and submit to hand restraints, which he refused to comply with staff orders. I then observed inmate Cranston yank on the blanket of inmate W. Kessler, which almost caused him to fall off the top rack. Cpl. Alder and I gave inmate Cranston a direct order to cease with his actions and submit to hand restraints to which he refused to comply. Inmate Cranston continued to state, "It's time for you to get out of this cell!" in an aggressive tone, while yanking on inmate Kessler's blanket again. Inmate Cranston then climbed up on the rack and began to strike inmate Kessler in the facial area with a closed fist. At this time, Cpl. Alder and I deployed a short burst of MK-3 oc spray (MFG:2021, Lot #29519, PMF #08421) to regain control over inmate Cranston. Both inmates were placed in hand restraints and escorted to showers for decontamination and seen by medical. Inmate Cranston was placed on Behavior Control by Major J. Sterling. Disciplinary action was taken. End of Report.
```

### Use of Force (chemical agents, taser, forced restraint) · incident 2

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 8/19/2023 at approximately 10:42pm Cpl. Grant Koffler observed Inmate Cano, Nicklaus ADC#658751 and Inmate Johnson, Chrishopher ADC#175052 strike Inmate Pruitt, Deshun ADC#180105 several times in the face and body area with closed fists. Inmate Pruitt ran around 13 barracks and positioned himself near the barrack door. I, Sergeant Daniel Whitfield, drew my state issued taser and ordered all inmates except Inmate Pruitt to exit the day room. I ordered Inmate Pruitt to exit 13 barracks and submit to hand restraints to which he complied. Then I resecured 13 barracks door and Inmate Pruitt was escorted to Restrictive Housing. I ordered Inmates Cano and Johnson to exit the barracks one at a time and submit to hand restraints to which they both complied. Both inmates were escorted to Restrictive Housing with out further incident. Witness statements, drug tests yielding negative results, and photos were collected from all three inmates. All inmates were seen by medical and separation alerts were requested. Inmate Pruitt was released back to general population because he did not fight back.
```

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 8/19/2023 at approximately 10:42pm I, Cpl. Grant Koffler, observed Inmate Cano, Nicklaus ADC#658751 and Inmate Johnson, Chrishopher ADC#175052 strike Inmate Pruitt, Deshun ADC#180105 several times in the face and body area with closed fists. Inmate Pruitt ran around 13 barracks and positioned himself near the barrack door. Staff ordered each inmate to exit the barracks one at a time to be escorted to Restrictive Housing without incident. Due to the above stated facts I, Cpl. Grant Koffler, am charging Inmate Cano, Nicklaus ADC#658751 and Inmate Johnson, Chrishopher ADC#175052 with major rule violation 4-8. Pending DCR.
```

### Use of Force (chemical agents, taser, forced restraint) · incident 3

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> ⚠️ NEEDS YOUR EDIT — non-standard time format. No code can fix this without changing what the report says.

```text
On 7/29/23 at approximately 11:45AM Cpl. Cody Williams observed Inmate Navarro, Jose #228141 choking Inmate Pearson, Danny #230847 on the floor in the dayroom of (Zone 1) 8 Barracks. At this time, Cpl. Williams radioed for assistance. Both inmates were involved in assaulting one another until responding staff arrived. The door was opened to 8 Barracks at which time both Inmates were given orders to lay face down. Inmate Navarro refused. Cpl. Reyes gave more direct orders to face down to which he refused; a short burst of chemical agents was deployed (MK-3 .7% Cone Serial #06989 Exp. Date 2023) to the facial area of Inmate Navarro. Sgt. Moreno arrived where he pointed his Taser at Navarro gave direct orders to lay face down to which he refused. Cpl. Reyes deployed a secondary short burst. Inmate Navarro was still non-compliant and was resisting staff to which Sgt. Guthrie, Sgt. Moreno, Cpl. Nash, and Cpl. Reyes forcibly placed Navarro in hand restraints. Inmate Pearson was placed in hand restraints. Both inmates were escorted directly to Restrictive Housing and seen by medical later. Inmate Navarro was afforded the opportunity to decontaminate. Photographs were taken, separation notification was generated, and video footage was downloaded. Disciplinary action taken.
```

---

## PREA

*6 incident(s), 10 report(s)*

### PREA · incident 1 — **matched set**

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 6/6/2023 at approximately 10:22pm Corporal Terri Guthrie was conducting a security check of 8 barracks when Inmate Sims, Paul ADC#173338 sexually proposed her by stating, “Do you want to fuck?” Cpl. Guthrie notified me, Sergeant Daniel Whitfield, and I ordered Inmate Sims to the hallway and placed hand restraints on him. I escorted inmate Sims to Restrictive Housing and placed him in the holding cell. Inmate Sims was seen by medical staff and pictures were taken.
```

**Short summary**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space, ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On 6/6/2023 at approximately 10:22pm Corporal Terri Guthrie was conducting a security check of 8 barracks when Inmate Sims, Paul ADC#173338 sexually proposed her by stating, “Do you want to fuck?” Inmate Sims was escorted to Restrictive Housing. Disciplinary action taken.
```

### PREA · incident 2

**First person (005 narrative)**  <sub>`Cover_Letter.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 9-7-23 at approximately 7:30pm I, Sergeant Daniel Whitfield, was informed by Inmate Langston, Miles ADC#208317 that his property was stolen from his rack when he was in the dayroom of 12 Barracks. On 9-7-23 at approximately 7:30pm I started my investigation by reviewing camera footage and observed on 9-7-23 at approximately 7:19pm Inmate Cardwell, Daniel ADC# 210463 went to rack 38 that is assigned to Inmate Langston and opened the unsecured property box and removed several items and placed them into a laundry bag. Then Inmate Cardwell went to rack 15 and stored the bag there. A short time later I went to 12 barracks rack 15 and searched it but was unable to find any property similar to the property stolen. Camera footage was reviewed, and I observed Inmate Cardwell removing items one at a time from his box and carrying them to several different locations in 12 barracks. I couldn’t determine if these items were stolen property or to whom they went to. Due to this none of the stolen property was able to be recovered. I conducted an interview with Inmate Langston in which he stated he had a verbal altercation with Inmate Whitlock, Charles ADC# 213562, and Inmate Hobbs, Seth ADC#216158 earlier that day, and believed Inmate Whitlock convinced Inmate Hobbs to steal his property. Inmate Langston would not disclose what the verbal altercation was about. I then conducted an interview with inmates Whitlock and Hobbs and they both stated they were not involved in the property being stolen from Inmate Langston. I conducted an interview with Inmate Cardwell, and he initially disclosed that he was removing his property from Inmate Langston’s box but on 9-11-2023 I reinterviewed Inmate Cardwell to which he retracted his earlier statement and disclosed that inmate Ackley, Patrick ADC#218153 told him to steal Inmate Langston’s property due to Inmate Langston wiping semen on Inmate Hobbs’s pillow. The PREA check list was initiated and all proper notifications were completed. Inmate Langston was interviewed and stated he was waiting for his turn in the shower and witnessed Inmate Hobbs masturbating and felt that Inmate Hobbs had intentionally left his semen in the shower as a “sexual suggestion”. At this time Inmate Langston admitted to wiping the semen up with a rag and placing it on Inmate Hobbs’s pillow. Inmate Hobbs was interviewed, and he verbally stated that he masturbated in the shower but refused to write it on his witness statement. I reviewed camera footage and observed Inmate Langston shaving his head in the bathroom area and briefly glanced at Inmate Hobbs in the shower then exited the bathroom area to continue shaving at his rack. No physical contact was observed or alleged between the two inmates. Due to the fact the incident happened several days ago no physical evidence was able to be collected. I placed both inmates in Restrictive Housing until the completion of the investigation. I interviewed Inmate Ackley and he verbally stated he did not tell Inmate Cardwell to steal anything but refused to write a statement. On 9-11-23 at approximately 11:30pm I concluded my investigation with the following findings: Inmate Hobbs exposed himself masturbating while in the shower and left his semen on the floor. Inmate Langston found this offensive and retrieved the semen with a rag and wiped it on Inmate Hobbs’s pillow.  Inmates Whitlock and Ackley are not being charged with instigating Inmate Cardwell to steal commissary from Inmate Langston due to lack of supporting evidence. Inmate Cardwell is being charged with theft and lying during an investigation due to his first statement stating the property taken from Inmate Langston’s box was his. Inmate Langston and Hobbs were seen by medical staff and photos were taken. Inmate Langston requested to talk to a victim advocate and the chaplain was notified. A separation alert was generated, and video footage was downloaded. Disciplinary action initiated.
```

**First person (005 narrative)**  <sub>`Cover_Letter_2.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 9-7-23 at approximately 7:30pm I, Sergeant Daniel Whitfield, was informed by Inmate Langston, Miles ADC#208317 that his property was stolen from his rack when he was in the dayroom of 12 Barracks. On 9-7-23 at approximately 7:30pm I started my investigation by reviewing camera footage and observed on 9-7-23 at approximately 7:19pm Inmate Cardwell, Daniel ADC# 210463 went to rack 38 that is assigned to Inmate Langston and opened the unsecured property box and removed several items and placed them into a laundry bag. Then Inmate Cardwell went to rack 15 and stored the bag there. A short time later I went to 12 barracks rack 15 and searched it but was unable to find any property similar to the property stolen. Camera footage was reviewed, and I observed Inmate Cardwell removing items one at a time from his box and carrying them to several different locations in 12 barracks. I couldn’t determine if these items were stolen property or to whom they went to. Due to this none of the stolen property was able to be recovered. I conducted an interview with Inmate Langston in which he stated he had a verbal altercation with Inmate Whitlock, Charles ADC# 213562, and Inmate Hobbs, Seth ADC#216158 earlier that day, and believed Inmate Whitlock convinced Inmate Hobbs to steal his property. Inmate Langston would not disclose what the verbal altercation was about. I then conducted an interview with inmates Whitlock and Hobbs and they both stated they were not involved in the property being stolen from Inmate Langston. I conducted an interview with Inmate Cardwell, and he initially disclosed that he was removing his property from Inmate Langston’s box but on 9-11-2023 I reinterviewed Inmate Cardwell to which he retracted his earlier statement and disclosed that inmate Ackley, Patrick ADC#218153 told him to steal Inmate Langston’s property due to Inmate Langston wiping semen on Inmate Hobbs’s pillow. The PREA check list was initiated and all proper notifications were completed. Inmate Langston was interviewed and stated he was waiting for his turn in the shower and witnessed Inmate Hobbs masturbating and felt that Inmate Hobbs had intentionally left his semen in the shower as a “sexual suggestion”. At this time Inmate Langston admitted to wiping the semen up with a rag and placing it on Inmate Hobbs’s pillow. Inmate Hobbs was interviewed, and he verbally stated that he masturbated in the shower but refused to write it on his witness statement. I reviewed camera footage and observed Inmate Langston shaving his head in the bathroom area and briefly glanced at Inmate Hobbs in the shower then exited the bathroom area to continue shaving at his rack. No physical contact was observed or alleged between the two inmates. Due to the fact the incident happened several days ago no physical evidence was able to be collected. I placed both inmates in Restrictive Housing until the completion of the investigation. I interviewed Inmate Ackley and he verbally stated he did not tell Inmate Cardwell to steal anything but refused to write a statement. On 9-11-23 at approximately 11:30pm I concluded my investigation with the following findings: Inmate Hobbs exposed himself masturbating while in the shower and left his semen on the floor. Inmate Langston found this offensive and retrieved the semen with a rag and wiped it on Inmate Hobbs’s pillow.  Inmates Whitlock and Ackley are not being charged with instigating Inmate Cardwell to steal commissary from Inmate Langston due to lack of supporting evidence. Inmate Cardwell is being charged with theft and lying during an investigation due to his first statement stating the property taken from Inmate Langston’s box was his. Inmate Langston and Hobbs were seen by medical staff and photos were taken. Inmate Langston requested to talk to a victim advocate and the chaplain was notified. A separation alert was generated, and video footage was downloaded. Disciplinary action initiated.
```

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 9-7-23 at approximately 7:30pm I, Sergeant Daniel Whitfield, was informed by Inmate Langston, Miles ADC#208317 that his property was stolen from his rack when he was in the dayroom of 12 Barracks. On 9-7-23 at approximately 7:30pm I started my investigation by reviewing camera footage and observed on 9-7-23 at approximately 7:19pm Inmate Cardwell, Daniel ADC# 210463 went to rack 38 that is assigned to Inmate Langston and opened the unsecured property box and removed several items and placed them into a laundry bag. Then Inmate Cardwell went to rack 15 and stored the bag there. A short time later I went to 12 barracks rack 15 and searched it but was unable to find any property similar to the property stolen. Camera footage was reviewed, and I observed Inmate Cardwell removing items one at a time from his box and carrying them to several different locations in 12 barracks. I couldn’t determine if these items were stolen property or to whom they went to. Due to this none of the stolen property was able to be recovered. I conducted an interview with Inmate Langston in which he stated he had a verbal altercation with Inmate Whitlock, Charles ADC# 213562, and Inmate Hobbs, Seth ADC#216158 earlier that day, and believed Inmate Whitlock convinced Inmate Hobbs to steal his property. Inmate Langston would not disclose what the verbal altercation was about. I then conducted an interview with inmates Whitlock and Hobbs and they both stated they were not involved in the property being stolen from Inmate Langston. I conducted an interview with Inmate Cardwell, and he initially disclosed that he was removing his property from Inmate Langston’s box but on 9-11-2023 I reinterviewed Inmate Cardwell to which he retracted his earlier statement and disclosed that inmate Ackley, Patrick ADC#218153 told him to steal Inmate Langston’s property due to Inmate Langston wiping semen on Inmate Hobbs’s pillow. The PREA check list was initiated and all proper notifications were completed. Inmate Langston was interviewed and stated he was waiting for his turn in the shower and witnessed Inmate Hobbs masturbating and felt that Inmate Hobbs had intentionally left his semen in the shower as a “sexual suggestion”. At this time Inmate Langston admitted to wiping the semen up with a rag and placing it on Inmate Hobbs’s pillow. Inmate Hobbs was interviewed, and he verbally stated that he masturbated in the shower but refused to write it on his witness statement. I reviewed camera footage and observed Inmate Langston shaving his head in the bathroom area and briefly glanced at Inmate Hobbs in the shower then exited the bathroom area to continue shaving at his rack. No physical contact was observed or alleged between the two inmates. Due to the fact the incident happened several days ago no physical evidence was able to be collected. I placed both inmates in Restrictive Housing until the completion of the investigation. I interviewed Inmate Ackley and he verbally stated he did not tell Inmate Cardwell to steal anything but refused to write a statement. On 9-11-23 at approximately 11:30pm I concluded my investigation with the following findings: Inmate Hobbs exposed himself masturbating while in the shower and left his semen on the floor. Inmate Langston found this offensive and retrieved the semen with a rag and wiped it on Inmate Hobbs’s pillow.  Inmates Whitlock and Ackley are not being charged with instigating Inmate Cardwell to steal commissary from Inmate Langston due to lack of supporting evidence. Inmate Cardwell is being charged with theft and lying during an investigation due to his first statement stating the property taken from Inmate Langston’s box was his. Inmate Langston and Hobbs were seen by medical staff and photos were taken. Inmate Langston requested to talk to a victim advocate and the chaplain was notified. A separation alert was generated, and video footage was downloaded. Disciplinary action initiated.
```

### PREA · incident 3

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 9-2-2023 at approximately 9:00pm I, Sergeant Daniel Whitfield, was notified by the Arkansas Crime Information Hotline that Inmate Williams, Kristan ADC#152659 placed a phone call on the PREA hotline at 9-1-23 at 5:39pm to complain about his 48-hour relief. At no time did Inmate Williams state any PREA related issues. Inmate Williams was counseled about the misuse of the PREA Hotline, and he is aware this is abuse of the Hotline. Due to the above stated facts I, Sergeant Daniel Whitfield, am charging Inmate Williams, Kristan ADC#152659 with rule violation 2-5, 12-3. Pending DCR.
```

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space, ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On 9-2-2023 at approximately 9:00pm I, Sergeant Daniel Whitfield, was notified by the Arkansas Crime Information Hotline that Inmate Williams, Kristan ADC#152659 placed a phone call on the PREA hotline at 9-1-23 at 5:39pm to complain about his 48-hour relief. At no time did Inmate Williams state any PREA related issues. Inmate Williams was counseled about the misuse of the PREA Hotline, and he is aware this is abuse of the Hotline. Disciplinary action taken.
```

### PREA · incident 4

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
I, Sergeant Daniel Whitfield, was assigned as the D-shift Restrictive Housing Supervisor from the dates 3-1-2023 to 5-1-2023 at the North Central Unit. At no time have I or am I aware of any ADC employee sexually harassing or retaliating against inmate Pertuit, Ryan ADC#147192. Furthermore, all trays fed in Restrictive Housing during my shift are chosen from the food cart at random and given to the inmates in the same condition as they are delivered from the kitchen. I, nor any officer that I supervise has placed any item in inmate Pertuit food tray. At no time have I shown any person inmate Pertuit’s EOMIS file. All employees that I supervise have remand professional at all times when interaction with inmate Pertuit.
```

### PREA · incident 5

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ⚠️ NEEDS YOUR EDIT — ends with a statement closer. No code can fix this without changing what the report says.

```text
On 9-7-23 at approximately 7:30pm I, Sergeant Daniel Whitfield, was informed by Inmate Langston, Miles ADC#208317 that his property was stolen from his rack when he was in the dayroom. On 9-7-23 at approximately 7:30pm I started my investigation by reviewing camera footage and observed on 9-7-23 at approximately 7:19pm Inmate Cardwell, Daniel ADC# 210463 went to rack 38 that is assigned to Inmate Langston and opened the unsecured property box and removed several items and placed them into a laundry bag. I conducted an interview with Inmate Cardwell, and he initially disclosed that he was removing his property from the box but on 9-11-2023 I reinterviewed Inmate Cardwell to which he retracted his earlier statement and disclosed that inmate Ackley, Patrick ADC#218153 told him to steal Inmate Langston’s property due to Inmate Langston wiping semen on Inmate Hobbs’s pillow. The PREA check list was initiated and all proper notifications were completed. Inmate Langston was interviewed and stated he was waiting for his turn in the shower and witnessed Inmate Hobbs masturbating and felt that Inmate Hobbs had intentionally left his semen in the shower as a “sexual suggestion”. At this time Inmate Langston admitted to wiping the semen up with a rag and placing it on Inmate Hobbs’s pillow. Inmate Hobbs was interviewed, and he verbally stated that he masturbated in the shower but refused to write it on his witness statement. Inmate Ackley verbally stated he did not tell Inmate Cardwell to steal anything but refused to write a statement. On 9-11-23 at approximately 11:30pm I concluded my investigation with the following finding: Inmate Hobbs exposed himself masturbating while in the shower and left his semen on the floor. Inmate Langston found this offensive and retrieved the semen with a rag and wiped it onto Inmate Hobbs’s pillow. Inmate Langston and Hobbs were seen by medical staff and photos were taken. Inmate Langston requested to talk to a victim advocate and the chaplain was notified. Disciplinary action taken. A separation alert was generated, and video footage was downloaded.
```

### PREA · incident 6

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
At approximately 11:00p.m on 10/13/23 I, Cpl. Kailee Boverhof was working my assigned post of 6 and 7 barracks. At this time, I, Cpl. Boverhof was in the 6 and 7 barracks control booth when I observed Inmate Wilbourn, Keyonte ADC# 172070 in the top tier shower of 6 barracks, staring down at me while using his left hand to stroke his erect penis, masturbating for sel-gradification. I notified Sgt. Meshia Evans, Inmate Wilbourn ADC# 172070 was given a direct order to step out into the hallway where he was given a second order to submit to hand restraints to which he complied. Inmate Wilbourn was then escorted to the Infirmary by security without further incident.
```

---

## Contraband

*2 incident(s), 3 report(s)*

### Contraband · incident 1 — **matched set**

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
Due to the above stated facts I, Sgt. Daniel Whitfield, am charging Inmate Richerdson, Jacob ADC# 162481, and Inmate Walton, Wesley ADC# 177422 with major rule violation 3-5, 7-4, 9-5. Pending DCR
```

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On November 11, 2023, at approximately 7:48pm Sgt. Daniel Whitfield witnessed an object in the front of Inmate Richerdson, Jacob ADC# 162481’s pants. He placed Inmate Richerdson into hand restraints and escorted him to Restrictive Housing. Once in the holding cell Inmate Richerdson was searched and a used chip bag was found containing several pieces of fried chicken. Sgt. Whitfield questioned Inmate Richerdson and he stated he retrieved them from ODR a few minutes ago. Sgt. Whitfield reviewed camera footage and noticed Inmate Richerdson and Inmate Walton, Wesley ADC# 177422 entering the ODR when they were walking to the library for library call. Inmate Walton was escorted to Restrictive Housing. Inmate Walton and his rack (12 Barracks/ Rack 10) was searched but no fried chicken was found. Photos were taken and both inmates were returned to their assigned barracks. A 401 Confiscation Form was completed, and the contraband was thrown away due to it being food items. Disciplinary action taken.
```

### Contraband · incident 2

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ⚠️ NEEDS YOUR EDIT — medical detail in the narrative. No code can fix this without changing what the report says.

```text
On 8/15/2023 at approximately 5:15am I, Cpl. Sterling Joans, was providing security in the chow hall when I observed 3 pills fall from Inmate Pelham, Jason’s ADC#129161 back pocket. I retrieved the pills from the floor and sent Inmate Pelham back to his assigned barracks. Photos were taken of the pills and identified by medical staff as Levetiracetam 500mg that are prescribed to Inmate Pelham but not authorized to carry on his person. A 401 form was completed, and the contraband was placed in locker BB. Due to the above stated facts I, Cpl. Sterling Joans, am charging Inmate Pelham, Jason ADC#129161 with rule violation 7-1 and 12-3 for barracks rule 36.
```

---

## Medical Emergency (no disciplinary)

*6 incident(s), 9 report(s)*

### Medical Emergency (no disciplinary) · incident 1 — **matched set**

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 1-10-24 at approximately 8:00pm I, Sgt. Daniel Whitfield, was notified that Inmate Aday, Billy ADC# 135331 was having a possible seizure in 10 barracks. I escorted infirmary staff to 10 barracks where Inmate Aday was sitting on the side of his rack. I assisted Inmate Aday in a wheelchair and escorted him to the infirmary. Inmate Aday was afforded medical treatment and was placed in the ward for observation. A drug test was conducted yielding negative results, and photographs were taken.
```

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 1-10-24 at approximately 8:00pm observed Inmate Aday, Billy ADC# 135331 having what appeared to be a seizure. Sgt. Daniel Whitfield escorted infirmary staff to 10 barracks where Inmate Aday was sitting on the side of his rack. Sgt. Whitfield assisted Inmate Aday in a wheelchair and escorted him to the infirmary. Inmate Aday was afforded medical treatment and was placed in the ward for observation. A drug test was conducted yielding negative results, and photographs were taken.
```

### Medical Emergency (no disciplinary) · incident 2

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 6/11/2023 at approximately 12:16am inmate Malone, Colin ADC#180229 went into 8 barracks dayroom and started to have a seizure. Cpl. Miles Bemies, Cpl. Miles Draper, Cpl. Alan Vance, Sgt. Jake Guthrie and I, Sgt. Daniel Whitfield, entered 8 barracks and secured inmate Malone’s head to keep it from striking the floor. Once medical staff arrived, and inmate Malone’s seizure stopped, the responding staff assisted inmate Malone to the gurney and escorted him to the infirmary. Medical staff evaluated inmate Malone and ordered 4-hour observation. Inmate Malone was escorted to the ward and assisted to a mattress on the floor. Photos were taken and a drug test was given yielding negative results.
```

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 6/11/2023 at approximately 12:16am inmate Malone, Colin ADC#180229 went into 8 barracks dayroom and started to have a seizure. Cpl. Miles Bemies, Cpl. Miles Draper, Cpl. Alan Vance, Sgt. Jake Guthrie and I, Sgt. Daniel Whitfield, entered 8 barracks and secured inmate Malone’s head to keep it from striking the floor. Once medical staff arrived, and inmate Malone’s seizure stopped, the responding staff assisted inmate Malone to the gurney and escorted him to the infirmary. Medical staff evaluated inmate Malone and ordered 4-hour observation. Inmate Malone was escorted to the ward and assisted to a mattress on the floor. Photos were taken and a drug test was given yielding negative results.
```

### Medical Emergency (no disciplinary) · incident 3

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 10/23/23 at approximately 7:30p.m. Inmate Aday, Billy ADC# 135331 started to have what appeared to be a seizure in 10 Barracks. I, Cpl. Jake Vance entered 10 barracks and secured Inmate Aday’s head to keep it from striking the floor. Once medical staff arrived, and Inmate Aday’s seizure stopped, I assisted Inmate Aday to the gurney and escorted him to the infirmary. Medical staff evaluated Inmate Aday and informed Lt. John Downing that he would need to be sent to Baxter Regional Medical Center via ambulance due to him losing consciousness during his possible seizure. The emergency gate pass was approved by Duty Warden Cpt. Brandt Ashford at 8:48pm. At 8:50pm Inmate Aday was escorted by Sgt. Jake Guthrie in the ambulance and Cpl. Miles Draper in the chase vehicle to Baxter Regional Medical Center. All notifications were made.
```

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 10/23/23 at approximately 7:30p.m. Inmate Aday, Billy ADC# 135331 started to have what appeared to be a seizure in 10 Barracks. I, Sgt. Daniel Whitfield, entered 10 barracks and secured the area. Once medical staff arrived, and Inmate Aday’s seizure stopped, I assisted Inmate Aday to the gurney and escorted him to the infirmary. Medical staff evaluated Inmate Aday and informed Lt. John Downing that he would need to be sent to Baxter Regional Medical Center via ambulance due to him losing consciousness during his possible seizure. The emergency gate pass was approved by Duty Warden Cpt. Brandt Ashford at 8:48pm. At 8:50pm Inmate Aday was escorted by Sgt. Jake Guthrie in the ambulance and Cpl. Miles Draper in the chase vehicle to Baxter Regional Medical Center. All notifications were made.
```

### Medical Emergency (no disciplinary) · incident 4

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
At approximately 9:36pm Cpl. Austin Deforest notified control center that inmate Oleson, Warren ADC#142950 was having a seizure in 14 barracks. I, Sgt. Daniel Whitfield, entered 14 barracks and cleared the dayroom of inmates. I approached inmate Oleson that was laying in rack 3 and he was appearing to have what appeared to be a seizure. Once Inmate Oleson stopped, I assisted him to his feet and escorted him to the gurney in the dayroom. I escorted inmate Oleson and medical staff to the infirmary where medical staff evaluated him and ordered 4 hr observation. Inmate Oleson was escorted to the ward and assisted to a mat placed onto the ground. Pictures were taken and drug tests were given, yielding negative results on all inmates.
```

### Medical Emergency (no disciplinary) · incident 5

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
At approximately 8:30pm Inmate Terry, Lawrence ADC#181670 started to have what appeared to be seizure on south yard. When medical staff arrived inmate Terry was assisted to a wheelchair and escorted to the infirmary. Medical staff evaluated inmate Terry and ordered 4-hour observation. Inmate Malone was escorted to the ward and assisted to a mattress on the floor.
```

### Medical Emergency (no disciplinary) · incident 6

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space, rank abbreviation missing its period. Normalized automatically before use; judge it on content.

```text
On 12-5-2023 Sgt. Dusten Foster was notified that Inmate Carruth, Elgie ADC#137860 was shaking. Sgt Foster radioed for a wheelchair to be brought to 3 barracks. Inmate Carruth was assisted to a wheelchair and escorted to medical. Medical treatment was offered to Inmate Carruth, and he was placed in the infirmary ward for observation. Drug test was conducted on yielding negative results. Photographs were taken. 3
```

---

## Investigation / Findings

*5 incident(s), 7 report(s)*

### Investigation / Findings · incident 1

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 12-23-23 at approximately 8:00pm I, Sgt. Daniel Whitfield, opened an investigation after reviewing camera footage from 12-18-23. On 12-18-23 at approximately 9:05pm I observed Inmate Hubbs, Trevis ADC# 153915 and Inmate Martinez, Miguel ADC# 147232 horse playing by holding down Inmate Etherton, Darin ADC# 153292 to his rack. I interviewed each inmate individually and all involved inmates stated it was horseplay and they were all friends. I collected witness statements from the involved inmates. On 12-23-23 at approximately 9:00pm I concluded my investigation with the following finding: Inmate Hubbs and Inmate Martinez held down Inmate Etherton to his rack in a horseplaying manner. Disciplinary action taken against Inmate Hubbs and Martinez but not Inmate Etherton due to him not horseplaying back.
```

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 12-23-23 at approximately 8:00pm I, Sgt. Daniel Whitfield, opened an investigation after reviewing camera footage from 12-18-23. On 12-18-23 at approximately 9:05pm I observed Inmate Hubbs, Trevis ADC# 153915 and Inmate Martinez, Miguel ADC# 147232 horse playing by holding down Inmate Etherton, Darin ADC# 153292 to his rack. I interviewed each inmate individually and all involved inmates stated it was horseplay and they were all friends. I collected witness statements from the involved inmates. On 12-23-23 at approximately 9:00pm I concluded my investigation with the following finding: Inmate Hubbs and Inmate Martinez held down Inmate Etherton to his rack in a horseplaying manner. Due to the above stated facts I, Sgt. Daniel Whitfield, am charging Inmate Hubbs, Trevis ADC# 153915 Martinez, Miguel ADC# 147232 with rule violation 2-17.
```

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 12-23-23 I, Sgt. Daniel Whitfield, reviewed camera footage from 12-18-23 at approximately 9:05pm and observed Inmate Hubbs, Trevis ADC# 153915 and Inmate Martinez, Miguel ADC# 147232 horse playing by holding down Inmate Etherton, Darin ADC# 153292 to his rack. I interviewed each inmate individually and all involved inmates stated it was horseplay and they were all friends. I collected witness statements from the involved inmates. Due to the above stated facts I, Sgt. Daniel Whitfield, am charging Inmate Hubbs, Trevis ADC# 153915 Martinez, Miguel ADC# 147232 with rule violation 2-17.
```

### Investigation / Findings · incident 2

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 7/12/2023 at approximately 10:30pm I, Sergeant Daniel Whitfield, was approached by Inmate Leclaire, Michael #181119 and he stated that he was given a cut slip instructing him to move to 7 barracks. Inmate Leclaire stated that he couldn’t move to 7 barracks because he was assaulted by 3 inmates housed in that barracks while he was working on field utility. I initiated an investigation at 10:30pm by gathering witness statements from inmates Whitney, Braydon #178931, Martinez, Angel #147232, and Stapleton, Shane #153759 then concluded my investigation at 11:50pm with the following findings: Inmates Whitney, Martinez, Stapleton all stated that they did not threaten, or assault inmate Leclaire and they have no problem with him. An Enemy Alert request was generated, and Inmate Leclaire was rehoused to 10 barracks.
```

### Investigation / Findings · incident 3

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ⚠️ NEEDS YOUR EDIT — non-standard time format. No code can fix this without changing what the report says.

```text
On 7/24/2023 I, Sgt. Grant Cross, was on duty as North Central Unit's Fusion Center Coordinator. At approximately 3:00PM I received information that Inmate Ely, Doncurian ADC# 146513, staff dining attendant, had been preparing Sandwiches and giving them to Inmate Croston, Detrick ADC# 131172. I immediately started an investigation into the matter by collecting statements and reviewing video footage. I concluded my investigation on 7/28/2023 at approximately 7:30AM with the following findings. Inmate Ely utilized his assigned work area to prepare a sandwich for Inmate Croston. He then placed the sandwich at the end of the Officer Dining Hallway and while Inmate Croston reported to treatment call he grabbed the sandwich (See attached photographs). During this investigation both Inmates were questioned to which they lied about how Inmate Croston obtained the sandwich and where it had came from (See attached statements). Therefore, due to the above stated facts both Inmates were written a major disciplinary.
```

### Investigation / Findings · incident 4

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 9-7-23 at approximately 7:30pm I, Sergeant Daniel Whitfield, was informed by Inmate Langston, Miles ADC#208317 that his property was stolen from his rack when he was in the dayroom. On 9-7-23 at approximately 7:35pm I started my investigation by reviewing camera footage and interviewing inmates. On 9-7-23 at approximately 10:30pm I concluded my investigation with the following finding: At 7:19pm Inmate Cardwell, Daniel ADC# 210463 went to rack 38 that is assigned to Inmate Langston and opened the unsecured property box and removed several items and placed them into a laundry bag. Then Inmate Cardwell went to rack 15 and stored the bag there. A short time later I went to 12 barracks rack 15 and searched it but was unable to find any property similar to the property stolen. Camera footage was reviewed, and several unidentified Inmate were seen around rack 15 before I was able to search the rack. Due to this none of the stolen property was able to be recovered. I conducted an interview with Inmate Langston to which he stated he had a verbal altercation with Inmate Whitlock, Charles ADC# 213562 and Inmate Hobbs, Seth ADC#216158  I rehoused inmate Langston and collected witness statements from all involved inmates. Due to the above stated facts I, Sergeant Daniel Whitfield, am charging Inmate Langston, Miles ADC#208317 with rule violation 7-4. Pending DCR.
```

### Investigation / Findings · incident 5

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 11-21-2023 I, Sgt. Daniel Whitfield, received a statement from Unit Chaplain Patrick McCown stating he received information about Inmate Hazelrigg, Michael ADC# 163177 and Inmate Clifton, Marks ADC# 97680 drawing a penis onto each other’s pants. On 11-21-2023 at approximately 11:00pm I initiated an investigation by interviewing and collecting statements from both inmates. Inmate ???? stated that he drew a penis onto Inmate ??? pants
```

---

## Other Rule Violation

*27 incident(s), 41 report(s)*

### Other Rule Violation · incident 1 — **matched set**

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On 1-11-24 at approximately 1:27am I, Sgt. Daniel Whitfield, was notified about suspicious activity in 13 barracks. I immediately started an investigation. I reviewed camera footage and observed Inmate Paech, Tommy ADC# 149225 and Inmate Bass, Kyston ADC# 170694 aggressively pushing each other and Inmate Bass pinning Inmate Paech to his rack. I called both inmates individual out of the barracks, placed on hand restraints, then escorted them to Restrictive Housing. I concluded my investigation on 1-11-24 at approximately 3:00am with the following finding: both Inmate Paech and Inmate Bass both actively participated in a physical altercation with each other. Photos were taken, and drug tests were conducted yielding negative results. A separation alert was generated. Both inmates were seen by medical staff. Inmate Paech was rehoused to 12 barracks and Inmate Bass was returned to 13 barracks. Disciplinary action taken.
```

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 1-11-24 at approximately 1:27am I, Sgt. Daniel Whitfield, was notified about suspicious activity in 13 barracks. I immediately started an investigation. I reviewed camera footage and observed Inmate Paech, Tommy ADC# 149225 and Inmate Bass, Kyston ADC# 170694 aggressively pushing each other and Inmate Bass pinning Inmate Paech to his rack. I called both inmates individual out of the barracks, placed on hand restraints, then escorted them to Restrictive Housing. I concluded my investigation on 1-11-24 at approximately 3:00am with the following finding: both Inmate Paech and Inmate Bass both actively participated in a physical altercation with each other. Photos were taken, and drug tests were conducted yielding negative results. A separation alert was generated. Both inmates were seen by medical staff. Inmate Paech was rehoused to 12 barracks and Inmate Bass was returned to 13 barracks. Due to the above stated facts I, Sgt. Daniel Whitfield, am charging Inmate Paech, Tommy ADC# 149225 Inmate Bass, Kyston ADC# 170694 with rule violation 4-8.
```

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 1-11-24 at approximately 1:27am Cpl. Willam observed Inmate Paech, Tommy ADC# 149225 run from the bottom tier of 13 barracks to the top tier and witnessed suspicious movement from the back of the top tier. Sgt. Daniel Whitfield was notified and after review of camera footage he observed Inmate Paech and Inmate Bass, Kyston ADC# 170694 aggressively pushing each other and Inmate Bass pinning Inmate Paech to his rack. Both inmates were escorted to Restrictive Housing where photos were taken, and drug tests were conducted yielding negative results. A separation alert was generated. Both inmates were seen by medical staff. Inmate Paech was rehoused to 12 barracks and Inmate Bass was returned to 13 barracks.
```

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On 1-11-24 at approximately 1:27am Cpl. Colin Barrett observed suspicious activity in 13 barracks and notified Sgt. Daniel Whitfield. Sgt. Whitfield reviewed camera footage and observed Inmate Paech, Tommy ADC# 149225 and Inmate Bass, Kyston ADC# 170694 aggressively pushing each other and Inmate Bass pinning Inmate Paech to his rack. Sgt. Whitfield called both inmates individual out of the barracks, placed on hand restraints, then escorted them to Restrictive Housing. Photos were taken, and drug tests were conducted yielding negative results. A separation alert was generated. Both inmates were seen by medical staff. Inmate Paech was rehoused to 12 barracks and Inmate Bass was returned to 13 barracks. Disciplinary action taken.
```

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On 1-11-24 at approximately 1:27am Sgt. Daniel Whitfield was notified about suspicious activity in 13 barracks. He immediately started an investigation. He reviewed camera footage and observed Inmate Paech, Tommy ADC# 149225 and Inmate Bass, Kyston ADC# 170694 aggressively pushing each other and Inmate Bass pinning Inmate Paech to his rack. Both inmates were escorted to Restrictive Housing. Sgt. Whitfield concluded his investigation on 1-11-24 at approximately 3:00am with the following finding: both Inmate Paech and Inmate Bass both actively participated in a physical altercation with each other. Photos were taken, and drug tests were conducted yielding negative results. A separation alert was generated. Both inmates were seen by medical staff. Inmate Paech was rehoused to 12 barracks and Inmate Bass was returned to 13 barracks. Disciplinary action taken.
```

### Other Rule Violation · incident 2 — **matched set**

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
At approximately 8:26pm I, Cpl. Kailee Boverhof, was working my assigned post of 6 and 7 barracks. While standing in 6 and 7 control booth I noticed Inmate McKinley, Emmit #117368 with his glasses on in the shower staring down at me with his right hand below his waist moving in a back-and-forth motion. Once Inmate McKinley and I made eye contact he jerked his right hand up and began washing himself. At this time, I moved to the doorway of 6 and 7 control booth in an attempt to not be directly in front of the shower area that Inmate McKinley was in. While looking around to maintain security in both barracks. I noticed Inmate McKinley multiple times swapping hands below his waist while moving them in a back-and-forth motion. At this time, I notified Sgt. Daniel Whitfield to come to North 1 and I gave inmate McKinley a direct order to get out of the shower to which he did not comply. Sgt. Whitfield and Cpl. Anthony Vredenburg gave Inmate McKinley a direct order to step out into the hallway. Once in the hallway Inmate McKinley was given another direct order to submit to hand restraints and was escorted to Restrictive Housing by Sgt. Whitfield and Cpl. Vredenburg with no further incident. Due to the about stated facts I, Cpl. Kailee Boverhof, am charging Inmate McKinley, Emmit #117368 with rule violation 10-3, 12-3. Pending DCR.
```

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On November 10, 2023, at approximately 8:26pm I, Sgt. Daniel Whitfield, was informed by Cpl. Kailee Boverhof that she observed Inmate McKinley, Emmit #117368 masturbating while staring at her in 6 barracks shower. I entered 6 barracks and ordered Inmate McKinley to get dressed and exit the barracks. Once in the hallway I applied hand restraints and escorted him to Restrictive Housing without incident. I took photos of Inmate McKinley and downloaded video footage of 6 barracks.
```

**Short summary**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On November 10, 2023, at approximately 8:26pm Cpl. Kailee Boverhof was in 6 and 7 control booth when she observed Inmate McKinley, Emmit ADC# 117368 taking a shower in the top tier shower of 6 barracks. While staring at Cpl. Boverhof, Inmate McKinley had his right hand below his waist moving his arm in a back and forth motion. Inmate McKinley was ordered to exit the barracks and was placed in hand restraints. Inmate McKinley was escorted to Restrictive Housing without incident. Photos were taken and video footage was downloaded. McKinley was seen by medical staff. Disciplinary action taken.
```

### Other Rule Violation · incident 3 — **matched set**

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 11-12-23 at approximately 11:45pm, I, Cpl. Anthony Vredenburg, as conduction a security check in 7 barracks and noticed Inmate Etherton, Darin ADC# 153296 had several fresh tattoos on his head that was red and raised. Specifically: Back of head: flames and skull, left side: Viking face, right side: Jesus face, Top of head: Angel wings.  I questioned Inmate Etherton and he stated he had a bunch of new tattoos not documented. Inmate Etherton was afforded medical treatment and photographs were taken of the tattoos. Due to the above stated facts I, Cpl. Anthony Vredenburg, am charging Inmate Etherton, Darin ADC# 153296 with major rule violation 2-11. Pending DCR.
```

**Short summary**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On 11-12-23 at approximately 11:45pm, Cpl. Anthony Vredenburg was conducting a security check in 7 barracks and noticed Inmate Etherton, Darin ADC# 153296 had a fresh tattoo on his head that was red and raised. Cpl. Vredenburg questioned Inmate Etherton and he stated he had a bunch of new tattoos not documented. Inmate Etherton was afforded medical treatment and photographs were taken of the tattoos. Disciplinary action taken.
```

### Other Rule Violation · incident 4 — **matched set**

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 11-16-23 at approximately 9:30pm I, Cpl. Kurdt Gaona, open the 5 Barracks door to allow Inmate Johnson, Dustin ADC# 178244 to enter 5 Barracks due to a housing change. Inmates Everett, Miles ADC# 109614, Henigan, Tyler ADC# 663246, Wilson, Jesse ADC# 179221, Morgan, Michael ADC# 137123 were standing at 5 Barracks entrance and stated, “You need to take him out”, “He can’t come back in here”. I took these statements and the fact that the inmates were standing in the doorway not allowing Inmate Johnson to enter the barracks as a direct threat to the safety and security of the unit. I closed the door and notified my supervisor. Inmate Johnson was rehoused. Inmates Everett, Henigan, Wilson, Morgan were individually sent down to the supervisor’s office where they were placed in hand restraints and escorted to Restrictive Housing. Due to the about stated facts I, Cpl. Kurdt Gaona, am charging Inmates Everett, Miles ADC# 109614, Henigan, Tyler ADC# 663246, Wilson, Jesse ADC# 179221, Morgan, Michael ADC# 137123 with major rule violation 1-1, 2-13.
```

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ends with a statement closer. Normalized automatically before use; judge it on content.

```text
On 11-16-23 at approximately 9:30pm Cpl. Kurdt Gaona opened the 5 Barracks door to allow Inmate Johnson, Dustin ADC# 178244 to enter 5 Barracks due to a housing change. Inmates Everett, Miles ADC# 109614, Henigan, Tyler ADC# 663246, Wilson, Jesse ADC# 179221, Morgan, Michael ADC# 137123 were standing at 5 Barracks entrance and stated, “You need to take him out”, “He can’t come back in here”. Cpl. Gaona took these statements and the fact that the inmates were standing in the doorway not allowing Inmate Johnson to enter the barracks as a direct threat to the safety and security of the unit. He closed the door and notified his supervisor. Inmate Johnson was rehoused to 9 Barracks. Inmates Everett, Henigan, Wilson, Morgan were individually sent down to the supervisor’s office where they were placed in hand restraints and escorted to Restrictive Housing. Disciplinary action taken.
```

### Other Rule Violation · incident 5 — **matched set**

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 11-29-23 at approximately 10:28pm I, Cpl. Edward Wells, was providing security at the Gym when I observed Inmate Burton, Kenneth ADC# 161520 jump while playing basketball and when coming down his head made contact onto Inmate Trevor, Ladarius’s ADC# 167825 right elbow. Photos were taken, and both inmates were afforded medical treatment. Drug tests were conducted on both inmates yielding negative results. Once released from medical both inmates returned to their assigned barracks.
```

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 11-29-23 at approximately 10:28pm Cpl. Edward Wells was providing security at the Gym when he observed Inmate Burton, Kenneth ADC# 161520 jump while playing basketball and when coming down his head made contact onto Inmate Trevor, Ladarius’s ADC# 167825 right elbow. Photos were taken, and both inmates were afforded medical treatment. Drug tests were conducted on both inmates yielding negative results. Once released from medical care both inmates returned to their assigned barracks.
```

### Other Rule Violation · incident 6 — **matched set**

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ⚠️ NEEDS YOUR EDIT — non-standard time format. No code can fix this without changing what the report says.

```text
On 12-19-2023 at approximately 10:55PM I, Sgt. Daniel Whitfield, escorted medical staff to 13 barracks. I observed Inmate Gatlin, Miles ADC# 182042 limping his left foot at the base of the stairs. I assisted Inmate Gatlin into the wheelchair and escorted him to the Infirmary. Inmate Gatlin was afforded medical care. A drug test was conducted yielding negative results, and photographs were taken. Once released from medical, Inmate Gatlin returned to his assigned barracks.
```

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> ⚠️ NEEDS YOUR EDIT — non-standard time format. No code can fix this without changing what the report says.

```text
On 12-19-2023 at approximately 10:55PM Inmate Gatlin, Miles ADC# 182042 fell while walking down the stairs in 13 Barracks. Medical responded with a wheelchair and Sgt. Daniel Whitfield escorted Inmate Gatlin to the Infirmary. Inmate Gatlin was afforded medical care. A drug test was conducted yielding negative results, and photographs were taken. Once released from medical, Inmate Gatlin returned to his assigned barracks.
```

### Other Rule Violation · incident 7 — **matched set**

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 1-30-24 at approximately 4:42am I, Sgt. Daniel Whitfield, escorted Inmate Morris, Damien ADC# 181528 to the infirmary due to him losing consciousness in 13 barracks. Photos and a witness statement were taken. A drug test was conducted yielding negative results. Inmate Morris was given treatment by medical staff and released to return to 13 Barracks.
```

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 1-30-24 at approximately 4:42am Sgt. Daniel Whitfield escorted Inmate Morris, Damien ADC# 181528 to the infirmary due to him losing consciousness in 13 barracks. Photos and a witness statement were taken. A drug test was conducted yielding negative results. Inmate Morris was given treatment by medical staff and released to return to 13 Barracks.
```

### Other Rule Violation · incident 8 — **matched set**

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 2-3-24 at approximately 8:07pm I, Sergeant Daniel Whitfield, escorted medical staff to 9 barracks with a wheelchair due to Cpl. Alan Vance stating on the radio that Inmate Douglas, Jessie ADC# 164999 fell on the stairs. I assisted Inmate Douglas into the wheelchair and escorted him to the Infirmary. Photos and a witness statement were taken. A drug test was conducted yielding negative results. Inmate Douglas was given treatment by medical staff and released to return to 9 Barracks.
```

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 2-3-24 at approximately 8:07pm Inmate Douglas, Jessie ADC# 164999 fell on the stairs. Sgt. Daniel Whitfield escorted medical staff to 9 Barracks, then assisted Inmate Douglas to the wheelchair. Inmate Douglas was escorted to the Infirmary and afforded medical care. Photos and a witness statement were taken. A drug test was conducted yielding negative results. Inmate Douglas was given treatment by medical staff and released to return to 9 Barracks.
```

### Other Rule Violation · incident 9 — **matched set**

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 2-7-24 at approximately 10:36pm I, Sgt. Daniel Whitfield, escorted medical staff to 12 barracks with a wheelchair due to Cpl. Luke Huett stating on the radio that Inmate Sterling, Marcus ADC# 554807 jumped off his rack and hurt his ankle. I assisted Inmate Sterling into the wheelchair and escorted him to the Infirmary. Photos and a witness statement were taken. A drug test was conducted yielding negative results. Inmate Douglas was given treatment by medical staff and released to return to 12 Barracks.
```

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 2-7-24 at approximately 10:36pm Sgt. Daniel Whitfield escorted medical staff to 12 barracks with a wheelchair due to Cpl. Luke Huett stating on the radio that Inmate Sterling, Marcus ADC# 554807 fell on the stairs. Sgt. Whitfield assisted Inmate Sterling into the wheelchair and escorted him to the Infirmary. Photos and a witness statement were taken. A drug test was conducted yielding negative results. Inmate Douglas was given treatment by medical staff and released to return to 12 Barracks.
```

### Other Rule Violation · incident 10

**First person (005 narrative)**  <sub>`Cover_Letter_NEW.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 1-29-24 at approximately 10:30pm I, Sergeant Daniel Whitfield, was given a request form authored by Inmate Marchetti, Peter ADC# 204118 stating that he would like Inmate Boyd, Bobby ADC# 205871 placed onto his separation alert list. I interviewed Inmate Marchetti in the supervisor’s office and he stated that in the past (no specific date given) Inmate Boyd would be mean to him if he didn’t get his way. Inmate Marchetti stated that Inmate Boyd pushed him into a wall but couldn’t remember the date and no incident was found to collaborate the statement. Inmate Marchetti verbally stated that no recent threats have been made. After collecting a verbal and written statement from Inmate Marchetti I find that there is not efficient evidence found to support Inmate Marchetti’s request for an enemy alert against Inmate Boyd. Inmate Boyd is currently housed in 12 Barracks and Inmate Marchetti is housed in 9 Barracks. I am forwarding the results to your office for further review.
```

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 1-29-24 at approximately 10:30pm I, Sergeant Daniel Whitfield, was given a request form authored by Inmate Marchetti, Peter ADC# 204118 stating that he would like Inmate Boyd, Bobby ADC# 205871 placed onto his separation alert list. I interviewed Inmate Marchetti in the supervisor’s office and he stated that in the past (no specific date given) Inmate Boyd would be mean to him if he didn’t get his way. Inmate Marchetti stated that Inmate Boyd pushed him into a wall but couldn’t remember the date and no incident was found to collaborate the statement. Inmate Marchetti verbally stated that no recent threats have been made. After collecting a verbal and written statement from Inmate Marchetti I find that there is not efficient evidence found to support Inmate Marchetti’s request for an enemy alert against Inmate Boyd. Inmate Boyd is currently housed in 12 Barracks and Inmate Marchetti is housed in 9 Barracks. I am forwarding the results to your office for further review.
```

### Other Rule Violation · incident 11

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 6/6/23 at approximately 10:22pm, I, Cpl. Terri Guthrie, was working my assigned post as security officer of 13 and 14 barracks on South 1 hall. As I conducted a security check in 8 barracks on South 1 hall, inmate Sims, Paul ADC#173338 passed by me and yelled, “Hey, you wanna fuck?” I notified my supervisor, Sgt. Daniel Whitfield, who then ordered inmate Sims out of 8 barracks into South 1 hallway, placed inmate Sims in hand restraints, and escorted inmate Sims to restrictive housing. For the above stated facts, I, Cpl. Terri Guthrie, am charging inmate Sims, Paul ADC#173338 with rule violations 10-2 and 11-1, pending DCR.
```

### Other Rule Violation · incident 12

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 6/9/2023 at approximately 9:15pm I, Sgt. Daniel Whitfield, was conducting a security check of 13 barracks with Cpt. Chris Alder and Cpl. Austin Deforest. Cpl. Alder approached inmate Brewer, Jamal ADC#172575 and started to question him about an earlier incident. Inmate Brewer became agitated and stated, “you can’t keep me, you’ll just have to cut me back out” and “you’re a bogus ass Niger! You’re a fucking liar!” Cpt. Alder ordered inmate Brewer to the hallway, and he complied. I placed hand restraints on inmate Brewer and escorted him to Restrictive Housing. Inmate Brewer was seen by medical staff and photos were taken.
```

### Other Rule Violation · incident 13

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ⚠️ NEEDS YOUR EDIT — non-standard time format. No code can fix this without changing what the report says.

```text
On 8-7-2023 I, Sergeant Daniel Whitfield, was observing breakfast feeding in the chow hall. At approximately 4:08AM I observed Inmate Troka, Owen ADC#178058 start to lose consciousness and place his head onto his food tray. I notified medical and when medical staff arrived I escorted inmate Troka to the infirmary. Inmate Troka was seen by medical staff and placed on observation in the ward. Pictures were taken and drug tests were given, yielding negative results. A short time later Inmate Troka was released back to his assigned barracks.
```

### Other Rule Violation · incident 14

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 8/9/2023 at approximately 8:40pm I, Sergeant Daniel Whitfield, responded to a radio call for an all available to south one. I responded and witnessed Sgt. Jake Guthrie, Sgt. Meshia Evans, Sgt. Lincoln Fowler Cpl. Colin Barrett, Cpl. Anthony Vredenburg restraining inmate Jackson, Darrin ADC#1798725 to the walkway. I called for leg restraints and Cpl. Alan Vance responded with them. Cpl. Austin Deforest placed the leg restraints on to inmate Jackson. Inmate Jackson was assisted to his feet and escorted to Restrictive Housing holding cell without further incident.
```

### Other Rule Violation · incident 15

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 8/24/2023 at approximately 6:45pm Cpl. Austin Deforest was providing security on south yard during yard call. Inmate Bates, Nichalas ADC#181576 informed Cpl. Deforest that he fell while playing basketball and hurt his knee. Inmate Bates was escorted to medical and seen by infirmary staff. Photos were taken and a drug test was conducted yielding negative results. A witness statement was collected from Inmate Bates, and he was released by medical back to his barracks after he was afforded treatment.
```

### Other Rule Violation · incident 16

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 9-12-23 at approximately 12:15am Cpl. Miles Draper escorted Inmate Woods, Grant ADC#140424 to the Boiler Room and witnessed boiler #1 spraying water. Inmate Woods shut down boiler #1. Maintenance Supervisor Roger Woods was notified, and a maintenance request was submitted.
```

### Other Rule Violation · incident 17

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 10/24/2023 at approximately 7:15p.m Inmate Shane, Fredrick ADC# 178648 was playing basketball in the gym during recreation call when he bit his tongue while jumping up for the basketball. Inmate Shane was taken to the Infirmary, a drug test was conducted yielding negative results, witness statements were collected, photographs were taken and Inmate Shane was sent back to his barracks without further incident.
```

### Other Rule Violation · incident 18

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> ⚠️ NEEDS YOUR EDIT — medical detail in the narrative. No code can fix this without changing what the report says.

```text
On 7/26/23 at 10:30pm Inmate Kirkwood, Troytaveis ADC# 156436 reported that he rolled his ankle while playing basketball to Cpl. Colin Barrett who was working as Gym security during recreation call. Inmate Kirkwood was sent to the Infirmary and treated by medical staff. Photographs were taken, a witness statement was written, and a drug test was completed yielding negative results.
```

### Other Rule Violation · incident 19

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> ⚠️ NEEDS YOUR EDIT — medical detail in the narrative. No code can fix this without changing what the report says.

```text
On 11/6/2023 at approximately 9:45pm Inmate Benson, Xavier ADC#174175 reported to Cpl. Alan Vance that he pulled his groin while playing basketball in the gym during recreation call. Inmate Benson was escorted to the Infirmary and treated by medical staff. Photographs were taken, a witness statement was written, and a drug test was completed yielding negative results. After being released from medical Inmate Benson was sent back to his assigned barracks without further incident.
```

### Other Rule Violation · incident 20

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ⚠️ NEEDS YOUR EDIT — medical detail in the narrative. No code can fix this without changing what the report says.

```text
On 11-6-23 I, Cpl. Alan Vance, was providing security in the gym during recreation call. At approximately 9:45pm Inmate Benson, Xavier ADC#174175 reported to me that he pulled a muscle in his leg when he was playing basketball. I informed the Infirmary and when medical staff arrived, I escorted Inmate Benson to the infirmary. Inmate Benson was treated by medical staff. Photographs were taken, a witness statement was written, and a drug test was completed yielding negative results. After being released from medical Inmate Benson was sent back to his assigned barracks without further incident.
```

### Other Rule Violation · incident 21

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 11-6-23 at approximately 10:10pm I, Sgt. Daniel Whitfield, responded to 13 barracks and observed Sgt. Meshia Evans place hand restraints onto Inmate Richardson, Joseph ADC# 663709. Sgt. Evans and I escorted Inmate Richardson to the infirmary, then to Restrictive Housing without incident.
```

### Other Rule Violation · incident 22

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> 🔧 AUTO-FIXABLE — ADC# written without a space. Normalized automatically before use; judge it on content.

```text
On 11-7-23 at approximately 5:20am Sgt. Daniel Whitfield was notified by Inmate Lumpkin, Roy ADC#178177 that he was having chest pains in 8 barracks. Sgt. Whitfield escorted Inmate Lumpkin to the Infirmary, and he was seen by medical staff. Photographs were taken, and a drug test was completed yielding negative results. Once Inmate Lumpkin was afforded medical treatment, he was sent back to 8 barracks without further incident.
```

### Other Rule Violation · incident 23

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 11-8-23 at approximately 5:00am I, Cpl. Dalton McMurray, was providing security at the pill window when I observed Inmate Griffith, Chris ADC# 180731 have a fresh tattoo on his face below his eyes that read “Humble Savage”. I questioned Inmate Griffith and he confirmed that it was a new tattoo but would not state how he received it. Photos were taken, and Inmate Griffith was seen by medical. Due to the above stated facts I, Cpl. Dalton McMurray, am charging Inmate Griffith, Chris ADC# 180731 with major rule violation 2-11, 12-3. Pending DCR.
```

### Other Rule Violation · incident 24

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 11-10-2023 at approximately 8:26pm I, Cpl. Anthony Vredenburg, observed Sgt. Daniel Whitfield place hand restraints onto Inmate McKinley, Emmit #117368. Then Sgt. Whitfield and I escorted Inmate McKinley from 6 Barracks to Restrictive Housing without incident.
```

### Other Rule Violation · incident 25

**Third person / supervisor**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 12-9-23 at approximately 4:40am Sgt. Daniel Whitfield was providing security in the central corridor during chow call when I observed Inmate Odom, Jason ADC# 150569 become disoriented and confused when walking to the pill window. Sgt. Whitfield escorted Inmate Odom to the infirmary where he was seen by medical staff and placed on 4-hour observation in the infirmary ward. A drug test was conducted yielding negative results, and photographs were taken. Inmate Odom returned to his assigned barrack once cleared by medical.
```

### Other Rule Violation · incident 26

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ⚠️ NEEDS YOUR EDIT — non-standard time format. No code can fix this without changing what the report says.

```text
On 12-18-2023 at approximately 9:17PM I, Sgt. Daniel Whitfield, applied hand restraints on to Inmate Hill, Chase ADC#174895 and escorted him from 7 barracks to Restrictive Housing without further incident.
```

### Other Rule Violation · incident 27

**First person (005 narrative)**  <sub>`005_templet.docx`</sub>

> ✅ CONFORMS — matches the style rulings. Judge it on content.

```text
On 12-22-23 I, Sgt. Daniel Whitfield, reviewed camera footage from 12-18-23 at approximately 9:05pm and observed Inmate Hubbs, Trevis ADC# 153915 horse playing by holding down Inmate Etherton, Darin ADC# 153292 to his rack. Due to the above stated facts I, Sgt. Daniel Whitfield, am charging Inmate Hubbs, Trevis ADC# 153915 with rule violation 2-17.
```

---
