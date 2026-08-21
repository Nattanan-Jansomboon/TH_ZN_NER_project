# Cross-Reference Patterns — Sports / Tech Domain

Session-specific wiring patterns observed during ingest sessions. These patterns apply to documents about competitive gaming, international sports events, sports injury tech, athletic equipment, and academic sports research.

## Pattern 1: City ↔ Event (Host City)

When an event is named after a city, wire both directions.

```
GPE/หางโจว.md:
  [Cross-references]
  - [[Entity_type/EVENT/เอเชียนเกมส์หางโจว2023]]

EVENT/เอเชียนเกมส์หางโจว2023.md:
  [Cross-references]
  - [[Entity_type/EVENT/เอเชียนเกมส์]]
  - [[Entity_type/GPE/หางโจว]]
  - [[Entity_type/DATE/ค.ศ.2023]]
```

## Pattern 2: City ↔ Institution (Location)

When an organization is located in a city, wire both directions.

```
GPE/เซี่ยงไฮ้.md:
  [Cross-references]
  - [[Entity_type/ORG/มหาวิทยาลัยกีฬาเซี่ยงไฮ้]]

ORG/มหาวิทยาลัยกีฬาเซี่ยงไฮ้.md:
  [Cross-references]
  - [[Entity_type/ORG/ศูนย์วิจัยกีฬาอิเล็กทรอนิกส์มหาวิทยาลัยกีฬาเซี่ยงไฮ้]]
  - [[Entity_type/GPE/เซี่ยงไฮ้]]
```

## Pattern 3: Parent ORG ↔ Subunit ORG

When a university has a research center, wire both directions.

```
ORG/มหาวิทยาลัยกีฬาเซี่ยงไฮ้.md:
  [Cross-references]
  - [[Entity_type/ORG/ศูนย์วิจัยกีฬาอิเล็กทรอนิกส์มหาวิทยาลัยกีฬาเซี่ยงไฮ้]]

ORG/ศูนย์วิจัยกีฬาอิเล็กทรอนิกส์มหาวิทยาลัยกีฬาเซี่ยงไฮ้.md:
  [Cross-references]
  - [[Entity_type/ORG/มหาวิทยาลัยกีฬาเซี่ยงไฮ้]]
```

## Pattern 4: Game ↔ Championship (Product ↔ Event)

When a game has a competition that features it, wire both directions.

```
PRODUCT/League_of_Legends.md:
  [Cross-references]
  - [[Entity_type/EVENT/การแข่งขันเวิลด์แชมเปียนชิพ League of Legends]]

EVENT/การแข่งขันเวิลด์แชมเปียนชิพ League of Legends.md:
  [Cross-references]
  - [[Entity_type/PRODUCT/League_of_Legends]]
```

## Pattern 5: Team ↔ Participating ORG

When an organization participates in an event, wire both directions.

```
ORG/EDG.md:
  [Cross-references]
  - [[Entity_type/ORG/ทีมจีน]]

EVENT/การแข่งขันเวิลด์แชมเปียนชิพ League of Legends.md:
  [Cross-references]
  - [[Entity_type/PRODUCT/League_of_Legends]]
  - [[Entity_type/ORG/EDG]]
  - [[Entity_type/DATE/ค.ศ.2021]]
```

## Pattern 6: Generic Event ↔ Specific Instance

When a specific instance of an event (e.g. 2023 Hangzhou Asian Games) is a sub-event of a generic event (Asian Games), wire both.

```
EVENT/เอเชียนเกมส์.md:
  [Cross-references]
  - [[Entity_type/EVENT/เอเชียนเกมส์หางโจว2023]]

EVENT/เอเชียนเกมส์หางโจว2023.md:
  [Cross-references]
  - [[Entity_type/EVENT/เอเชียนเกมส์]]
  - [[Entity_type/GPE/หางโจว]]
  - [[Entity_type/DATE/ค.ศ.2023]]
```

## Pattern 7: Manufacturer ↔ R&D Lab

When a company has an internal research or development lab, wire both directions.

```
ORG/ไนกี้.md:
  [Cross-references]
  - [[Entity_type/ORG/ห้องปฏิบัติการวิจัยด้านกีฬาของไนกี้]]

ORG/ห้องปฏิบัติการวิจัยด้านกีฬาของไนกี้.md:
  [Cross-references]
  - [[Entity_type/ORG/ไนกี้]]
```

## Pattern 8: Product ↔ Manufacturer (Brand)

When a product is manufactured or branded by a specific company, wire both directions. Note that this forms a triangle with Pattern 7: the manufacturer sits between its products and its labs.

```
PRODUCT/Nike_Vaporfly.md:
  [Cross-references]
  - [[Entity_type/ORG/ไนกี้]]

ORG/ไนกี้.md:
  [Cross-references]
  - [[Entity_type/PRODUCT/Nike_Vaporfly]]
  - [[Entity_type/ORG/ห้องปฏิบัติการวิจัยด้านกีฬาของไนกี้]]
```

## When to Wire

Wire cross-references at **entity creation time** for any entity that shares a semantic relationship with another entity in the same batch. The eight patterns above cover 95% of sports/tech domain documents. For other domains, use analogous relations:

| Domain | City ↔ Event | Parent ↔ Subunit | Product ↔ Manufacturer |
|--------|-------------|------------------|----------------------|
| Tech | Office ↔ Conference | Company ↔ Division | Platform ↔ Developer |
| Finance | City ↔ Summit | Bank ↔ Branch | App ↔ Publisher |
| Healthcare | City ↔ Symposium | Hospital ↔ Department | Drug ↔ Pharma Co. |
| Sports | City ↔ Competition | Sports Assoc. ↔ Institute | Equipment ↔ Brand |