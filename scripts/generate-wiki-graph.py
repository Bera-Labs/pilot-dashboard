#!/usr/bin/env python3
"""Generate wiki-graph.json from ~/wiki-superhuman/ concept pages.
Reads frontmatter confidence and wikilinks to build the intervention→outcome graph.
v2: Enriched — node descriptions, edge evidence details, wiki page links.
"""
import json, os, re, yaml
from pathlib import Path
from collections import defaultdict

WIKI = Path(os.path.expanduser("~/wiki-superhuman"))
CONCEPTS = WIKI / "concepts"
OUTPUT = Path(os.path.expanduser("~/.hermes/skills/stem-stack/pilot-dashboard/data/wiki-graph.json"))

# === NODE DESCRIPTIONS (pulled from wiki pages + research summaries) ===
NODE_DESC = {
    "sleep": "7-9 hours of consistent sleep. Strongest single intervention for cognitive function: improves executive function, attention, memory consolidation, and emotional regulation. Sleep deprivation directly impairs prefrontal cortex function — the same region compromised by stress and addiction.",
    "creatine": "5g/day creatine monohydrate. Meta-analysis of 16 RCTs (Xu et al., 2024): improves memory (SMD +0.31), attention, processing speed, and reduces mental fatigue. More effective in stressed/sleep-deprived populations. One of only two supplements with strong evidence for cognitive enhancement.",
    "nac": "N-acetylcysteine 1200-2400mg/day. Targets glutamate system, not dopamine directly. 2 meta-analyses + 4 RCTs showing craving reduction across methamphetamine, cocaine, nicotine, alcohol, and cannabis. Restores cystine-glutamate antiporter → normalizes glutamate in nucleus accumbens → reduces cravings. Does NOT directly reduce brain fog.",
    "omega3": "1-2g EPA+DHA/day. 58-RCT dose-response meta-analysis (Shahinfar et al., 2025): per 2000mg improves attention (SMD=0.98), memory (SMD=0.87), global cognition (SMD=1.08). GRADE: low-moderate certainty. Supports neuronal membrane fluidity and dopamine receptor function. No addiction-specific trials.",
    "resistance": "Resistance training 2-3x/week for 12+ weeks. Strong evidence for neuroplasticity (BDNF elevation, IGF-1 signaling). Moderate evidence for executive function improvement. Works through myokine signaling — muscles release irisin and cathepsin B that cross the blood-brain barrier.",
    "iron": "Iron supplementation ONLY if deficient (low ferritin). Meta-analysis of 18 studies (Fiani et al., 2025): improves fatigue (d=0.34) and cognition (d=0.46) in iron-deficient individuals. Zero effect if iron levels are normal. Test ferritin before supplementing.",
    "rhodiola": "Rhodiola rosea SHR-5 extract. Strong evidence for physical fatigue reduction and stress resilience. Evidence for mental/cognitive fatigue is mixed — 2025 RCT found 'trivial' effect on mental fog. Phase III RCT (2009) confirmed anti-fatigue effects under stress.",
    "curcumin": "Curcumin 800mg/day for ≥24 weeks. Meta-analysis of 9 RCTs (2025): improves global cognition but slow onset, effects primarily in older/Asian populations. Anti-inflammatory mechanism — reduces neuroinflammation. Not recommended for acute cognitive enhancement.",
    "cold_exposure": "2-5 minute cold shower or cold plunge. Weak evidence for dopamine recovery — primarily mechanistic (cold shock proteins, norepinephrine surge). No clinical trials for addiction recovery. May provide acute mood/motivation boost via sympathetic activation.",
    "omega3_addiction": "Omega-3 for addiction recovery specifically. Plausible mechanism (neuronal membrane support, dopamine receptor function, BDNF) but ZERO addiction-specific clinical trials exist. Recommendation: reasonable for general health, no evidence for recovery acceleration.",
    "tyrosine_mg_zn": "L-Tyrosine (dopamine precursor), Magnesium (NMDA modulation), Zinc (dopamine cofactor). Commonly recommended in recovery communities. Zero clinical trials for addiction recovery or cognitive enhancement from supplementation in non-deficient populations.",
    "taurine": "Taurine supplementation. Meta-analysis of 7 RCTs (2025): no significant effect on cognitive function. Previously thought to reduce mental fatigue — evidence does not support this claim.",
    "beetroot": "Beetroot juice/supplementation. Systematic review (2025): inconclusive for cognitive function. Nitric oxide mechanism plausible for cerebral blood flow but cognitive outcome data is insufficient.",
    "self_compassion": "Self-compassion practices: faster lapse recovery after relapse. Moderate evidence — self-compassion reduces shame spiraling that extends single misses into full behavioral collapse. Complements habit formation (reduces reset-button pattern). Not a standalone intervention.",
    "stress_protocol": "Biometric-triggered behavioral interrupt. Architecture: Whoop HRV/HR stress detection → Claude routes next action from Outliner task list → Katana single-slice execution (this hour only, no outcome thinking). Grounded in implementation intentions research (Gollwitzer, 1999). Design constraint: must be single-line under stress. Friction asymmetry: rule-following requires fewer steps than rule-breaking.",
    "exercise": "Aerobic + resistance exercise. Strongest evidence for cognitive enhancement: improves executive function, neuroplasticity (BDNF), reduces brain fog, accelerates dopamine recovery. 150+ min/week moderate or 75+ min/week vigorous. Multiple meta-analyses and RCTs across populations.",
    "mindfulness": "8-week MBSR or daily meditation practice. Strong evidence for attention (DMN-dlPFC anticorrelation), executive function, and stress reduction. Moderate evidence for craving reduction and self-control. Creates awareness gap between urge and action — the critical intervention window.",
    "habit_formation": "Building automatic routines instead of relying on willpower. 100-study meta-analysis (33K participants): high self-control individuals don't resist better — they automate. Key methods: implementation intentions (if-then plans, 2x success rate), environmental design (friction asymmetry), mindfulness (urge awareness). Fundamentally more sustainable than willpower training.",
    "willpower_training": "Training self-control as a muscle through repeated resistance. Weak evidence — replication crisis in ego-depletion literature. Some studies show small effects from practice, but habit formation consistently outperforms. Not recommended as primary strategy.",
    "dopamine_recovery": "Dopamine system recovery during abstinence. PET imaging (Volkow et al., 2015): DAT transporters recover within weeks, but dopamine release function may take months-years. DAT recovery ≠ functional recovery. Brain fog and anhedonia in early abstinence are caused by this dissociation. Exercise accelerates recovery through BDNF and neuroplasticity mechanisms.",
    "brain_fog": "Subjective cognitive impairment — mental fatigue, slow processing, poor concentration. In addiction recovery, caused by dopamine system dysfunction (DAT/release dissociation) plus sleep disruption, stress, and inflammation. Academic proxies: mental fatigue, cognitive impairment, processing speed deficits. No single biomarker — diagnosed via symptom cluster.",
}

# Outcome node descriptions
OUTCOME_DESC = {
    "executive_function": "Prefrontal cortex-mediated functions: planning, inhibition, working memory, cognitive flexibility. The 'CEO' of the brain. Impaired by stress, sleep deprivation, dopamine dysfunction. Improved by exercise, sleep, mindfulness, creatine.",
    "memory": "Declarative and working memory — encoding, storage, retrieval. Strongly improved by creatine (SMD +0.31), omega-3, exercise, and sleep. Consolidation occurs during sleep — sleep deprivation directly impairs memory formation.",
    "attention": "Sustained and selective attention. Strongly improved by sleep, mindfulness (DMN-dlPFC anticorrelation), creatine, and omega-3. Impaired by stress (amygdala hijack of attentional resources) and dopamine dysfunction.",
    "processing_speed": "Rate of information processing — how fast the brain converts input to output. Strongly improved by creatine. Affected by sleep deprivation, mental fatigue, and neuroinflammation. Measurable via reaction time and cognitive test batteries.",
    "mental_fatigue": "Subjective sense of cognitive exhaustion — the 'brain fog' proxy in academic research. Improved by creatine (strong), exercise (strong), sleep (strong), iron (if deficient). Not improved by taurine or beetroot (negative evidence).",
    "neuroplasticity": "Brain's capacity to reorganize and form new connections — BDNF, synaptogenesis, dendritic arborization. Strongly improved by exercise (especially resistance training) and sleep. The biological substrate of learning, recovery, and behavioral change.",
    "cravings": "Intense urge to engage in addictive behavior. Driven by glutamate dysregulation in nucleus accumbens. NAC strongest evidence for craving reduction (2 meta-analyses). Mindfulness moderate evidence (urge surfing). Exercise moderate (dopamine alternative).",
    "addiction_recovery": "Global recovery from substance or behavioral addiction. Multifactorial: requires craving reduction + cognitive recovery + habit replacement. NAC + exercise + habit formation is the evidence-backed stack. Self-compassion prevents relapse spirals.",
    "mood": "Emotional state — depression and anxiety symptoms. Strongly improved by exercise (effect size comparable to antidepressants for mild-moderate depression). Also improved by sleep and mindfulness. Affected by dopamine dysfunction in abstinence.",
    "physical_fatigue": "Muscular and cardiovascular exhaustion. Strongly reduced by Rhodiola (Phase III RCT), exercise training (paradoxical — acute fatigue, chronic improvement), and sleep. Distinct from mental fatigue — different mechanisms.",
    "stress": "Physiological and psychological stress response — HPA axis activation, cortisol, sympathetic arousal. Strongly reduced by mindfulness, Rhodiola, exercise, and sleep. The stress protocol targets the stress→avoidance transition specifically.",
    "self_control": "Capacity to override impulses and align behavior with long-term goals. Habit formation strongest evidence (100-study meta-analysis). Willpower training weak evidence. Mindfulness moderate (creates awareness gap). Stress protocol moderate (pre-loaded decisions).",
    "relapse": "Return to addictive behavior after period of abstinence. NAC strongest evidence for prevention (2 meta-analyses). Habit formation strong (automatic alternatives). Self-compassion moderate (prevents shame spiral → full relapse). The 5-7 day window is the highest-risk period during dopamine recovery.",
}

# === EDGE EVIDENCE DETAILS ===
EDGE_EVIDENCE = {
    # Exercise edges
    ("exercise", "executive_function"): "Multiple meta-analyses: aerobic exercise improves PFC-dependent executive functions. BDNF-mediated neuroplasticity. Effect strongest for moderate-intensity, 30-60 min sessions.",
    ("exercise", "neuroplasticity"): "Resistance training → myokine release (irisin, cathepsin B) → BDNF elevation → hippocampal neurogenesis. Aerobic exercise → increased cerebral blood flow → synaptogenesis. Well-replicated across animal and human studies.",
    ("exercise", "brain_fog"): "150+ min/week moderate exercise reduces subjective cognitive complaints. Mechanism: increased cerebral blood flow, dopamine normalization, anti-inflammatory effects. Strongest non-pharmacological intervention for brain fog.",
    ("exercise", "mental_fatigue"): "Acute exercise may increase mental fatigue but chronic training reduces baseline fatigue. Effect is dose-dependent — moderate intensity optimal. Complements sleep and creatine.",
    ("exercise", "addiction_recovery"): "Exercise provides alternative dopamine source during abstinence. Reduces cravings via endogenous opioid and endocannabinoid release. Moderate evidence — mechanism established, addiction-specific trials ongoing.",
    ("exercise", "dopamine_recovery"): "Costa et al. model: exercise accelerates dopamine system normalization through BDNF-TrkB signaling and reduced oxidative stress in dopaminergic neurons. Moderate evidence — mechanism established, human timeline data limited.",
    ("exercise", "mood"): "Effect size comparable to antidepressants for mild-moderate depression. Immediate mood elevation (endorphins) + sustained improvement (BDNF, neuroplasticity). Strongest evidence in all of exercise psychology.",
    # Sleep edges
    ("sleep", "brain_fog"): "Sleep deprivation directly impairs PFC function — reduced glucose metabolism in prefrontal regions. Single night of poor sleep measurably degrades attention and working memory. Most immediate intervention for acute brain fog.",
    ("sleep", "executive_function"): "PFC is the brain region most sensitive to sleep loss. Decision-making, inhibition, and cognitive flexibility degrade linearly with sleep debt. 7-9 hours is the optimal range — both under and oversleeping impair function.",
    ("sleep", "attention"): "Sustained attention is the cognitive domain most vulnerable to sleep loss. Psychomotor vigilance task (PVT) is the gold-standard measure — lapses increase exponentially after 16+ hours awake. Sleep restores baseline.",
    ("sleep", "memory"): "Memory consolidation occurs during slow-wave and REM sleep. Hippocampal replay during SWS transfers memories to cortex. Sleep deprivation after learning impairs retention — sleep is when learning 'sticks.'",
    # Mindfulness edges
    ("mindfulness", "attention"): "8-week MBSR → preserved attention on sustained tasks. DMN-dlPFC anticorrelation strengthened — reduced mind-wandering. Multiple RCTs, moderate-large effect sizes.",
    ("mindfulness", "executive_function"): "Mindfulness training increases PFC gray matter density and improves cognitive control. Mechanism: strengthened top-down regulation of amygdala by PFC. Effect accumulates over 8+ weeks of practice.",
    ("mindfulness", "stress"): "Mindfulness-Based Stress Reduction (MBSR) is the gold-standard intervention. Reduces cortisol, sympathetic arousal, and subjective stress. Creates gap between stressor and response — the same window the stress protocol targets.",
    ("mindfulness", "cravings"): "Urge surfing technique: observe craving without acting. Reduces craving intensity and duration. Moderate evidence from addiction-specific MBSR trials. Combines with NAC for dual-pathway craving reduction.",
    ("mindfulness", "self_control"): "Creates awareness of impulses BEFORE they become actions. This meta-cognitive gap is the mechanism — you can't redirect what you don't notice. Moderate evidence, complements habit formation.",
    # Creatine edges
    ("creatine", "memory"): "Meta-analysis of 16 RCTs (Xu 2024): SMD +0.31 for memory. More effective in stressed/sleep-deprived/fatigued populations — suggests mechanism is ATP buffering during cognitive load, not baseline enhancement.",
    ("creatine", "attention"): "Attention time and processing speed improved in creatine trials. GRADE: low certainty but consistent direction. Effect most pronounced under cognitive stress conditions — creatine's mechanism is energy buffer, not stimulant.",
    ("creatine", "processing_speed"): "Information processing speed improved across multiple RCTs. Mechanism: creatine → phosphocreatine → ATP regeneration during high-demand cognitive tasks. Particularly relevant for mental fatigue states.",
    ("creatine", "mental_fatigue"): "Anti-mental-fatigue effect is creatine's strongest cognitive claim. Reduces subjective mental exhaustion during prolonged cognitive tasks. Most relevant for brain fog recovery — directly targets the 'mental fatigue' symptom.",
    ("creatine", "brain_fog"): "Indirect evidence: creatine reduces mental fatigue, and mental fatigue is the primary academic proxy for brain fog. No direct 'brain fog' trials exist. Moderate confidence based on extrapolation from mental fatigue data.",
    # NAC edges
    ("nac", "cravings"): "2 meta-analyses (Winterlind 2024, Cuocina 2024) + 4 RCTs. Restores cystine-glutamate antiporter → normalizes glutamate in nucleus accumbens → reduces craving intensity. Effect size: moderate. Onset: days to weeks.",
    ("nac", "addiction_recovery"): "NAC reduces the core driver of relapse (cravings) across multiple substance classes. Combined with exercise (dopamine alternative) and habit formation (behavioral replacement) forms the evidence-backed recovery stack.",
    ("nac", "relapse"): "NAC's craving reduction translates to relapse prevention. ACCENT trial (Alias-Ferri 2026): craving trajectories are heterogeneous — NAC response varies by individual. Does not eliminate relapse risk; reduces probability.",
    # Resistance training edges
    ("resistance", "neuroplasticity"): "Resistance training → myokine cascade → BDNF elevation. Myokines (irisin, cathepsin B) cross blood-brain barrier. Strong evidence from both animal models and human trials. 12+ weeks for measurable structural changes.",
    ("resistance", "executive_function"): "Moderate evidence: resistance training improves executive function, especially in older adults. Mechanism: increased cerebral blood flow + BDNF → PFC structural maintenance. Less studied than aerobic exercise for cognition.",
    # Iron edges
    ("iron", "mental_fatigue"): "Iron improves fatigue ONLY in iron-deficient individuals (d=0.34). Effect disappears in iron-normal populations. Test ferritin before supplementing — unnecessary iron is pro-oxidative and potentially harmful.",
    ("iron", "memory"): "Memory improvement (d=0.46) only in iron-deficient populations. Iron is a cofactor for dopamine synthesis and myelination. Deficiency impairs cognition; supplementation above normal does not enhance it.",
    # Rhodiola edges
    ("rhodiola", "physical_fatigue"): "Strongest evidence for Rhodiola: Phase III RCT (2009) showed significant reduction in physical fatigue under stress. Mechanism: adaptogenic — modulates HPA axis and sympathetic response. SHR-5 extract is the studied form.",
    ("rhodiola", "stress"): "Anti-stress effect confirmed in multiple trials. Reduces cortisol response to acute stressors. The adaptogenic mechanism supports the stress protocol's goal of preventing stress → avoidance cascade.",
    ("rhodiola", "mental_fatigue"): "Mixed evidence. 2025 RCT: Rhodiola effect on mental fog described as 'trivial.' Earlier trials showed moderate benefit. Current recommendation: useful for physical fatigue/stress, insufficient evidence for cognitive fatigue specifically.",
    # Curcumin edges
    ("curcumin", "memory"): "Meta-analysis of 9 RCTs (2025): improves global cognition but slow onset (≥24 weeks). Effects primarily in older/Asian populations. Anti-inflammatory mechanism — reduces neuroinflammation that impairs cognition. Weak recommendation for acute use.",
    ("curcumin", "brain_fog"): "Weak evidence, primarily mechanistic. Curcumin reduces neuroinflammation which can cause brain fog. But no direct 'brain fog' trials. Slow onset (weeks-months) makes it unsuitable for acute intervention.",
    # Cold exposure edges
    ("cold_exposure", "dopamine_recovery"): "Weak evidence, primarily mechanistic. Cold exposure → norepinephrine surge → downstream dopamine modulation. Cold shock proteins may support neural repair. No clinical trials for addiction recovery. Used anecdotally for acute mood/motivation boost.",
    # Omega-3 edges
    ("omega3", "attention"): "58-RCT meta-analysis: per 2000mg EPA+DHA, attention improvement SMD=0.98. GRADE: low certainty (high heterogeneity between studies). Mechanism: neuronal membrane fluidity → improved signal transduction.",
    ("omega3", "memory"): "58-RCT meta-analysis: memory improvement SMD=0.87. More consistent than attention findings. Omega-3 is structural — incorporated into neuronal membranes over weeks-months, not acute effect.",
    ("omega3", "brain_fog"): "Weak evidence for brain fog specifically. Omega-3 supports general brain health but no trials use 'brain fog' as outcome. Recommendation: reasonable for long-term brain health, not for acute brain fog relief.",
    ("omega3_addiction", "addiction_recovery"): "Zero addiction-specific trials. Plausible mechanism (neuronal membrane support, dopamine receptor function) but untested. Recommendation: take for general health, do not rely on for addiction recovery.",
    ("omega3_addiction", "brain_fog"): "No direct evidence connecting omega-3 to brain fog reduction in addiction recovery. Extrapolated from general cognition data. Weak recommendation.",
    # None-evidence edges
    ("tyrosine_mg_zn", "brain_fog"): "ZERO clinical trials. L-Tyrosine is a dopamine precursor in theory but oral tyrosine supplementation does not reliably increase brain dopamine in non-deficient humans. Magnesium and zinc are essential minerals but supplementation above normal levels shows no cognitive benefit.",
    ("tyrosine_mg_zn", "dopamine_recovery"): "No evidence. Dopamine precursor theory is mechanistically appealing but clinically unsupported. Dopamine synthesis is rate-limited by tyrosine hydroxylase, not tyrosine availability, in non-deficient states.",
    ("taurine", "brain_fog"): "Meta-analysis of 7 RCTs (2025): no significant effect. Previously hypothesized to reduce mental fatigue — evidence now shows this claim is false. Do not use for brain fog.",
    ("beetroot", "brain_fog"): "Systematic review (2025): inconclusive. Nitric oxide mechanism (increased cerebral blood flow) is plausible but cognitive outcome data is insufficient. More research needed — current evidence does not support recommendation.",
    # Habit formation edges
    ("habit_formation", "self_control"): "100-study meta-analysis (33K participants): the highest self-control individuals have the strongest HABITS, not the strongest willpower. They automate behavior → never need to resist. Implementation intentions (if-then plans) double success rates. This is the evidence-based alternative to willpower training.",
    ("habit_formation", "addiction_recovery"): "Habit replacement is a core mechanism of addiction recovery. Replace the cue-routine-reward loop with a new routine that serves the same cue. Combined with NAC (cravings) and exercise (dopamine), this forms the complete evidence-backed recovery framework.",
    ("habit_formation", "relapse"): "Strongest evidence for relapse prevention among behavioral interventions. Automatic alternative behaviors don't require executive function during craving states — when PFC is compromised, habits still run. Implementation intentions specifically reduce relapse rates.",
    # Willpower training edges
    ("willpower_training", "self_control"): "Weak evidence. Ego-depletion theory (willpower as depletable resource) has faced replication crisis. Some studies show small training effects, but habit formation consistently and substantially outperforms. Not recommended as primary intervention.",
    # Self-compassion edges
    ("self_compassion", "relapse"): "Moderate evidence: self-compassion after lapse reduces probability of full relapse. Mechanism: shame is the amplifier that converts single miss → behavioral collapse. Self-compassion interrupts the shame spiral. Review only during scheduled sessions, never in the moment.",
    ("self_compassion", "addiction_recovery"): "Self-compassion supports sustained recovery by reducing the all-or-nothing crash that follows lapses. Complements habit formation (automatic behaviors don't need self-compassion) and NAC (cravings don't trigger shame). Part of the reset protocol.",
    # Stress protocol edges
    ("stress_protocol", "stress"): "Biometric-triggered protocol interrupts stress response before cognitive shutdown. Mechanism: pre-loaded if-then plan (implementation intention) linked to physiological signal. Gollwitzer (1999): if-then plans automate action initiation under cognitive load. Moderate evidence — protocol designed per implementation intentions research.",
    ("stress_protocol", "self_control"): "Pre-loaded decisions bypass the deliberation that fails under stress. When PFC is compromised, having a pre-decided action ready prevents the avoidance default from loading. Complements habit formation — protocol is a specific implementation of if-then planning.",
    ("stress_protocol", "relapse"): "The protocol targets the critical Phase 1→2 transition in the stress-avoidance-relapse cycle. By interrupting at the physiological signal (before cognitive shutdown and escape behavior), it prevents the cascade that leads to relapse. Moderate confidence — protocol design is sound, not yet independently tested.",
    ("stress_protocol", "cravings"): "Weak direct evidence for craving reduction. The protocol does not target cravings directly — it prevents the stress→avoidance→relapse chain. However, if cravings are stress-triggered, the protocol indirectly reduces craving frequency by reducing stress triggers.",
}

# Map wiki pages to graph nodes
WIKI_TO_NODE = [
    ("exercise-cognitive-enhancement", "exercise", "Exercise", "intervention", None),
    ("dopamine-recovery-neurobiology", "dopamine_recovery", "Dopamine Recovery", "outcome", None),
    ("mindfulness-cognitive-enhancement", "mindfulness", "Mindfulness", "intervention", None),
    ("supplements-brainfog-cognition", None, None, None, None),
    ("supplements-addiction-recovery", None, None, None, None),
    ("willpower-training", "willpower_training", "Willpower Training", "intervention", None),
    ("habit-formation-vs-willpower", "habit_formation", "Habit Formation", "intervention", None),
    ("brain-fog-mechanism", "brain_fog", "Brain Fog", "outcome", None),
    ("exercise-sleep-nutrition-synthesis", None, None, None, None),
    ("stress-protocol-katana", "stress_protocol", "Stress Protocol (Katana)", "intervention", None),
]

EXTRA_INTERVENTIONS = [
    ("sleep", "Sleep", "intervention", "high"),
    ("creatine", "Creatine", "intervention", "high"),
    ("nac", "NAC", "intervention", "high"),
    ("omega3", "Omega-3", "intervention", "medium"),
    ("resistance", "Resistance Training", "intervention", "medium"),
    ("iron", "Iron", "intervention", "medium"),
    ("rhodiola", "Rhodiola", "intervention", "medium"),
    ("curcumin", "Curcumin", "intervention", "low"),
    ("cold_exposure", "Cold Exposure", "intervention", "low"),
    ("omega3_addiction", "Omega-3 (addiction)", "intervention", "low"),
    ("tyrosine_mg_zn", "Tyrosine, Mg, Zn", "intervention", "none"),
    ("taurine", "Taurine", "intervention", "none"),
    ("beetroot", "Beetroot", "intervention", "none"),
    ("self_compassion", "Self-Compassion", "intervention", "medium"),
    ("stress_protocol", "Stress Protocol (Katana)", "intervention", "medium"),
]

EXTRA_OUTCOMES = [
    ("executive_function", "Executive Function"),
    ("memory", "Memory"),
    ("attention", "Attention"),
    ("processing_speed", "Processing Speed"),
    ("mental_fatigue", "Mental Fatigue"),
    ("neuroplasticity", "Neuroplasticity"),
    ("cravings", "Cravings"),
    ("addiction_recovery", "Addiction Recovery"),
    ("mood", "Mood / Depression"),
    ("physical_fatigue", "Physical Fatigue"),
    ("stress", "Stress"),
    ("self_control", "Self-Control"),
    ("relapse", "Relapse Prevention"),
]

EDGES = [
    ("exercise", "executive_function", "strong"),
    ("exercise", "neuroplasticity", "strong"),
    ("exercise", "brain_fog", "strong"),
    ("exercise", "mental_fatigue", "strong"),
    ("exercise", "addiction_recovery", "moderate"),
    ("exercise", "dopamine_recovery", "moderate"),
    ("exercise", "mood", "strong"),
    ("sleep", "brain_fog", "strong"),
    ("sleep", "executive_function", "strong"),
    ("sleep", "attention", "strong"),
    ("sleep", "memory", "moderate"),
    ("mindfulness", "attention", "strong"),
    ("mindfulness", "executive_function", "strong"),
    ("mindfulness", "stress", "strong"),
    ("mindfulness", "cravings", "moderate"),
    ("mindfulness", "self_control", "moderate"),
    ("creatine", "memory", "strong"),
    ("creatine", "attention", "strong"),
    ("creatine", "processing_speed", "strong"),
    ("creatine", "mental_fatigue", "strong"),
    ("creatine", "brain_fog", "moderate"),
    ("nac", "cravings", "strong"),
    ("nac", "addiction_recovery", "strong"),
    ("nac", "relapse", "strong"),
    ("omega3", "attention", "moderate"),
    ("omega3", "memory", "moderate"),
    ("omega3", "brain_fog", "weak"),
    ("resistance", "neuroplasticity", "strong"),
    ("resistance", "executive_function", "moderate"),
    ("iron", "mental_fatigue", "moderate"),
    ("iron", "memory", "moderate"),
    ("rhodiola", "physical_fatigue", "strong"),
    ("rhodiola", "stress", "strong"),
    ("rhodiola", "mental_fatigue", "weak"),
    ("curcumin", "memory", "weak"),
    ("curcumin", "brain_fog", "weak"),
    ("cold_exposure", "dopamine_recovery", "weak"),
    ("omega3_addiction", "addiction_recovery", "weak"),
    ("omega3_addiction", "brain_fog", "weak"),
    ("tyrosine_mg_zn", "brain_fog", "none"),
    ("tyrosine_mg_zn", "dopamine_recovery", "none"),
    ("taurine", "brain_fog", "none"),
    ("beetroot", "brain_fog", "none"),
    ("habit_formation", "self_control", "strong"),
    ("habit_formation", "addiction_recovery", "strong"),
    ("habit_formation", "relapse", "strong"),
    ("willpower_training", "self_control", "weak"),
    ("self_compassion", "relapse", "moderate"),
    ("self_compassion", "addiction_recovery", "moderate"),
    ("stress_protocol", "stress", "moderate"),
    ("stress_protocol", "self_control", "moderate"),
    ("stress_protocol", "relapse", "moderate"),
    ("stress_protocol", "cravings", "weak"),
]

page_to_node = {
    "brain-fog-mechanism": "brain_fog",
    "dopamine-recovery-neurobiology": "dopamine_recovery",
    "dopamine-recovery-protocol": None,
    "exercise-cognitive-enhancement": "exercise",
    "exercise-sleep-nutrition-synthesis": None,
    "habit-formation-vs-willpower": "habit_formation",
    "mindfulness-cognitive-enhancement": "mindfulness",
    "supplements-addiction-recovery": "nac",
    "supplements-brainfog-cognition": "creatine",
    "willpower-training": "willpower_training",
    "stress-protocol-katana": "stress_protocol",
}


def read_frontmatter(path):
    try:
        with open(path) as f:
            content = f.read()
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                fm = yaml.safe_load(content[3:end])
                return fm
    except Exception:
        pass
    return {}


def build_graph():
    nodes = []
    
    # Add interventions with rich descriptions
    for nid, label, ntype, conf in EXTRA_INTERVENTIONS:
        desc = NODE_DESC.get(nid, "")
        node = {"id": nid, "label": label, "type": ntype, "confidence": conf, "desc": desc}
        # Add wiki page link if it exists
        wiki_slug = None
        for slug, mapped_id, _, _, _ in WIKI_TO_NODE:
            if mapped_id == nid:
                wiki_slug = slug
                break
        if wiki_slug:
            node["wiki_page"] = f"concepts/{wiki_slug}"
        nodes.append(node)
    
    # Add outcomes with descriptions
    for oid, label in EXTRA_OUTCOMES:
        desc = OUTCOME_DESC.get(oid, "")
        nodes.append({"id": oid, "label": label, "type": "outcome", "desc": desc})
    
    # Enrich wiki-sourced nodes with frontmatter
    for slug, nid, label, ntype, _ in WIKI_TO_NODE:
        if nid is None:
            continue
        page_path = CONCEPTS / f"{slug}.md"
        fm = read_frontmatter(page_path) if page_path.exists() else {}
        conf = fm.get("confidence", "medium")
        
        existing = next((n for n in nodes if n["id"] == nid), None)
        if existing:
            existing["confidence"] = conf
            existing["wiki_page"] = f"concepts/{slug}"
    
    # Build edges with evidence descriptions
    edges = []
    for f, t, s in EDGES:
        edge = {"from": f, "to": t, "strength": s, "type": "evidence"}
        evidence_key = (f, t)
        if evidence_key in EDGE_EVIDENCE:
            edge["evidence"] = EDGE_EVIDENCE[evidence_key]
        edges.append(edge)
    
    # Add crosslinks from wiki pages
    seen_crosslinks = set()
    for md_file in sorted(CONCEPTS.glob("*.md")):
        slug = md_file.stem
        from_node = page_to_node.get(slug)
        if from_node is None:
            continue
        with open(md_file) as f:
            content = f.read()
        links = re.findall(r'\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]', content)
        for link in links:
            to_node = page_to_node.get(link)
            if to_node and to_node != from_node:
                key = (from_node, to_node)
                if key not in seen_crosslinks:
                    seen_crosslinks.add(key)
                    edges.append({
                        "from": from_node, "to": to_node,
                        "strength": "crosslink", "type": "crosslink"
                    })
    
    return {"nodes": nodes, "edges": edges}


if __name__ == "__main__":
    graph = build_graph()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(graph, f, indent=2)
    # Also copy to dashboard repo
    repo_output = Path("/root/pilot-dashboard/data/wiki-graph.json")
    repo_output.parent.mkdir(parents=True, exist_ok=True)
    with open(repo_output, "w") as f:
        json.dump(graph, f, indent=2)
    
    node_fields = sum(1 for n in graph["nodes"] if n.get("desc"))
    edge_fields = sum(1 for e in graph["edges"] if e.get("evidence"))
    print(f"✓ wiki-graph.json regenerated: {len(graph['nodes'])} nodes ({node_fields} with descriptions), {len(graph['edges'])} edges ({edge_fields} with evidence details)")
