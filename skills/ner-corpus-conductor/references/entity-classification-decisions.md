# Entity Classification Decisions — Sports & Technology Domain

Patterns observed during ingest of bilingual ZH-TH documents in the sports data and sports technology domain.

## Academic Journals and Publishing Bodies

| Candidate | Classify As | Reason |
|-----------|-------------|--------|
| Journal of Sports Research / 《体育学研究》 | ORG | Publishing institution / media outlet with ISSN, editorial board, regular issues |
| Sports and Science / 《体育与科学》 | ORG | Same logic — journal as publishing platform |

**Rule:** A journal name appearing in a context like "X published an article" or "X journal reports" refers to the publishing body (ORG), not an individual creative work. Only classify as WORK_OF_ART when referring to a specific one-off piece (article title, book title, song, film).

## Technology Systems and Platforms

| Candidate | Classify As | Reason |
|-----------|-------------|--------|
| VAR (Video Assistant Referee) | PRODUCT | Specific named technology system used in football — not a generic concept |
| Nike Vaporfly | PRODUCT | Specific named product series from a manufacturer |
| 智能穿戴设备 / อุปกรณ์สวมใส่อัจฉริยะ | TECHNICAL_TERM (IT Domain) | General class of technology, not a specific branded product |
| 碳板技术 / เทคโนโลยีแผ่นคาร์บอน | TECHNICAL_TERM (Engineering Domain) | Materials/engineering concept, not a branded product |

**Rule:** If it has a brand name + product model → PRODUCT. If it describes a category or concept of technology → TECHNICAL_TERM.

## Sports Analytics Metrics

| Candidate | Classify As | Reason |
|-----------|-------------|--------|
| 真实命中率 / อัตราการทำประตูที่แท้จริง (true shooting %) | TECHNICAL_TERM (IT Domain) | Data analytics metric — IT Domain (sports analytics) |
| 每回合得分 / แต้มต่อการครองบอล (points per possession) | TECHNICAL_TERM (IT Domain) | Data analytics metric — IT Domain |

**Rule:** Performance metrics and statistical measures in sports analytics belong to IT Domain (data analysis category of TECHNICAL_TERM), not Engineering.

## International Sports Organizations

| Candidate | Classify As | Reason |
|-----------|-------------|--------|
| World Athletics / 国际田联 | ORG | International governing body |
| NBA | ORG | Professional sports league / organization |

## Parent–Subunit ORG Relationships

| Parent ORG | Subunit ORG | Relationship |
|------------|-------------|--------------|
| 北京体育大学 | 中国体育大数据中心 | University → Research Center |
| Nike (耐克) | Nike Sports Research Lab (耐克运动研究实验室) | Company → R&D Lab |

**Cross-reference both directions at entity creation time.**