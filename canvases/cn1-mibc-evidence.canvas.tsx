import {
  BarChart,
  Callout,
  Card,
  CardBody,
  CardHeader,
  CollapsibleSection,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useHostTheme,
} from "cursor/canvas";

const TRIALS = [
  {
    study: "EV-ECLIPSE",
    totalN: 23,
    cn1N: 23,
    tier: "A",
    score: 98,
    setting: "Neoadjuvant EV+pembro → RC",
    outcome: "pCR primary — no results yet",
    color: "green" as const,
  },
  {
    study: "EV-302 (LN-only)",
    totalN: 886,
    cn1N: 207,
    tier: "B−",
    score: 55,
    setting: "1L metastatic/unresectable",
    outcome: "PFS HR 0.40; OS HR 0.46",
    color: "blue" as const,
  },
  {
    study: "NIAGARA (cN1)",
    totalN: 1063,
    cn1N: 58,
    tier: "B",
    score: 72,
    setting: "Perioperative durva+GC",
    outcome: "cN1 EFS HR 0.75 (NS)",
    color: "amber" as const,
  },
  {
    study: "KEYNOTE-905 (cN1)",
    totalN: 344,
    cn1N: 17,
    tier: "B−",
    score: 58,
    setting: "Perioperative EV+pembro (cis-inel)",
    outcome: "EFS HR 0.40; pCR 57%",
    color: "purple" as const,
  },
  {
    study: "SWOG 8710",
    totalN: 307,
    cn1N: 0,
    tier: "C",
    score: 15,
    setting: "NAC MVAC → RC (N0 only)",
    outcome: "5-y OS benefit — no cN+",
    color: "gray" as const,
  },
  {
    study: "CheckMate 274 (pN1)",
    totalN: 709,
    cn1N: 143,
    tier: "C-adj",
    score: 30,
    setting: "Adjuvant nivo post-RC",
    outcome: "DFS HR 0.70",
    color: "gray" as const,
  },
];

const chartData = TRIALS.map((t) => ({
  label: t.study,
  value: t.cn1N,
}));

const columns = [
  { key: "study", header: "Study", width: "18%" },
  { key: "totalN", header: "Total N", align: "right" as const, width: "8%" },
  { key: "cn1N", header: "cN1/cN+ n", align: "right" as const, width: "9%" },
  { key: "tier", header: "Tier", width: "7%" },
  { key: "score", header: "Fit", align: "right" as const, width: "6%" },
  { key: "setting", header: "Setting", width: "22%" },
  { key: "outcome", header: "Key outcome", width: "30%" },
];

export default function Cn1MibcEvidenceCanvas() {
  const theme = useHostTheme();

  return (
    <Stack gap={24} style={{ padding: 24, maxWidth: 1100 }}>
      <Stack gap={8}>
        <H1>cN1 cM0 MIBC — Evidence Patient Counts</H1>
        <Text tone="muted">
          pT2 HG, L1, PET+ external iliac node · perioperative intent · Source: wiki
          evidence registry · June 2026
        </Text>
      </Stack>

      <Callout tone="info">
        EV-ECLIPSE is the only trial designed for node-positive perioperative EV+pembro (~23
        patients). EV-302 has 207 lymph-node–only patients but in metastatic, not pre-cystectomy,
        setting. NIAGARA includes 58 cN1 patients with approved perioperative durvalumab+chemo.
      </Callout>

      <Grid columns={4} gap={16}>
        <Stat label="Best fit trial" value="EV-ECLIPSE" detail="n ≈ 23, Tier A" tone="positive" />
        <Stat label="Strongest EV+pembro data" value="n = 207" detail="EV-302 LN-only subgroup" />
        <Stat label="Approved perioperative IO" value="n = 58" detail="NIAGARA cN1 subgroup" />
        <Stat label="Czech NAC standard" value="n = 0" detail="SWOG 8710 enrolled cN0 only" tone="warning" />
      </Grid>

      <Card>
        <CardHeader title="Patients matching node-positive profile" />
        <CardBody>
          <BarChart
            data={chartData}
            title="Enrolled patients with cN1 / node-positive overlap by trial"
            xLabel="Clinical trial"
            yLabel="Patient count (n)"
            caption="Perioperative-relevant and adjuvant trials · cN1/cN+ overlap estimates from published reports"
            height={280}
          />
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Trial comparison registry" trailing={<Pill tone="info">12 studies</Pill>} />
        <CardBody style={{ padding: 0 }}>
          <Table
            columns={columns}
            rows={TRIALS.map((t) => ({
              study: t.study,
              totalN: t.totalN,
              cn1N: t.cn1N,
              tier: t.tier,
              score: t.score,
              setting: t.setting,
              outcome: t.outcome,
            }))}
          />
        </CardBody>
      </Card>

      <Grid columns={2} gap={16}>
        <Card>
          <CardHeader title="If cisplatin-eligible" />
          <CardBody>
            <Stack gap={12}>
              <Row gap={8}>
                <Pill tone="positive">Standard</Pill>
                <Text>NAC (SWOG 8710 meta-analyses) — no cN1 in RCTs</Text>
              </Row>
              <Row gap={8}>
                <Pill tone="positive">Approved IO</Pill>
                <Text>NIAGARA durva+GC — 58 cN1, subgroup NS</Text>
              </Row>
              <Row gap={8}>
                <Pill tone="warning">Investigational</Pill>
                <Text>EV+pembro — EV-ECLIPSE phase 2; EV-304 pending</Text>
              </Row>
            </Stack>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="If cisplatin-ineligible" />
          <CardBody>
            <Stack gap={12}>
              <Row gap={8}>
                <Pill tone="positive">Phase 3</Pill>
                <Text>KEYNOTE-905 EV+pembro — ~17 cN1 of 344</Text>
              </Row>
              <Row gap={8}>
                <Pill tone="info">Node-focused</Pill>
                <Text>EV-ECLIPSE — designed for cN+ before RC</Text>
              </Row>
              <Row gap={8}>
                <Pill tone="muted">Avoid</Pill>
                <Text>Carboplatin NAC (EAU: do not offer)</Text>
              </Row>
            </Stack>
          </CardBody>
        </Card>
      </Grid>

      <CollapsibleSection
        header={
          <Row gap={8}>
            <H3>Argument priority for oncologist visit</H3>
          </Row>
        }
      >
        <Stack gap={8} style={{ paddingTop: 8 }}>
          {[
            "1. EV-ECLIPSE — closest design match; acknowledge phase 2, no results",
            "2. EV-302 LN-only n=207 — proves EV+pembro beats chemo in nodal disease, wrong setting",
            "3. NIAGARA n=58 cN1 — approved perioperative alternative if cisplatin-fit",
            "4. SWOG/meta-analyses — doctor's baseline; cN+ from retrospective data only",
            "5. CheckMate 274 / AMBASSADOR — adjuvant backup if surgery leaves pN+",
          ].map((line) => (
            <Text key={line}>{line}</Text>
          ))}
        </Stack>
      </CollapsibleSection>

      <Text tone="muted" style={{ fontSize: 12, color: theme.muted }}>
        Agent: c:\dev\cancer\scripts\research_agent.py · Wiki:
        wiki/bladder-cancer/cn1-mibc-evidence-comparison.md
      </Text>
    </Stack>
  );
}
