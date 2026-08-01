![](images/dbc60010f24b0330a2dfc0a1ca95280688fbd8bd97b44dd0b2761987506d8e7f.jpg)

![](images/f35c505ea14b4c8e375501446889b9d587f953189a4fbf2367f46f727f8b5c47.jpg)

Deliverable Reference

: D1.4

Title

: System Requirements Document

Confidentiality Level : PU

Lead Partner

: Space Applications Services

Abstract

: This document presents the system requirements for MOSAR that were derived from the application and technology review, and the analysis of the operational and demonstration scenarios.

EC Grant N°

: 821996

Project Officer EC

: Christos Ampatzis (REA)

![](images/ed701402b226ebd575000059aba16feaedcc43308eaab572ab40aa51d927d163.jpg)

MOSAR is co-funded by the Horizon 2020 Framework Programme of the European Union

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=4>DOCUMENT APPROVAL SHEET</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Name</td><td rowspan=1 colspan=1>Organization</td><td rowspan=1 colspan=1>Date</td></tr><tr><td rowspan=1 colspan=1>Prepared andcross-review by:</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>Space Applications ServicesThales Alenia Space FranceThales Alenia Space UKSITAELGMVUniversity of StrathclydeGerman Aerospace Centre (DLR)MAG SOAR</td><td rowspan=1 colspan=1>28/06/2019</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=5>DOCUMENT CHANGE RECORD</td></tr><tr><td rowspan=1 colspan=1>Version</td><td rowspan=1 colspan=1>Date</td><td rowspan=1 colspan=1>Author</td><td rowspan=1 colspan=1>ChangedSections / Pages</td><td rowspan=1 colspan=1>Reason for Change / RID No</td></tr><tr><td rowspan=1 colspan=1>0.9.0</td><td rowspan=1 colspan=1>28/06/2019</td><td rowspan=1 colspan=1>Partners</td><td rowspan=1 colspan=1>All</td><td rowspan=1 colspan=1>Initial delivery for SRR review</td></tr><tr><td rowspan=1 colspan=1>1.0.0</td><td rowspan=1 colspan=1>01/09/2019</td><td rowspan=1 colspan=1>SpaceApplicationsUSTRAT</td><td rowspan=1 colspan=1>Section 2.2.1Section 2.2.2(FuncR_S118)Section 2.2.3(PerfR_S201/202)Section 2.2.7Section 3.3.1(FuncR_A113-116, B103)</td><td rowspan=1 colspan=1>Added section based on RID OG09-48Comment removed based on RIDOG09-49Edited based on RID OG09-50Edited based on RID OG09-51Edited based on RID OG09-53</td></tr></table>

## MOSAR - System Requirements Document

## Contents

1 Introduction 8   
1.1 Purpose and Scope. 8   
1.2 Document Structure 8   
1.3 Applicable Documents. . 8   
1.4 Reference Documents. . 8   
1.5 Acronyms. .. 9   
2 Modular Spacecraft Requirements . 10   
2.1 Mission Overview . 10   
2.2 Space Scenarios Requirements . 12   
2.2.1 Formalism . 12   
2.2.2 S100: Functional requirements [FuncR]. . 13   
2.2.3 S200: Performance requirements [PerfR] . 20   
2.2.4 S300: Interface requirements [IntRD] . 21   
2.2.5 S400: Design requirements [DesR].. . 22   
2.2.6 S500: Physical and resource requirements [PhyR].. . 23   
2.2.7 S600: Environmental and Operational requirements [OpR]. . 23   
2.2.8 S700: Safety requirements [SafR] . 25   
2.2.9 S800: Configuration and implementation requirements [ConfR] 29   
3 MOSAR Demonstrator Requirements . 31   
3.1 Demonstrator Overview . 31   
3.2 Formalism . 32   
3.3 System Requirements [Axxx] . 33   
3.3.1 A100: Functional requirements [FuncR]. . 33   
3.3.2 A200: Performance requirements [PerfR] . 37   
3.3.3 A300: Interface requirements [IntR] . 39   
3.3.4 A400: Design requirements [DesR]. . 40   
3.3.5 A500: Physical and resource requirements [PhyR]. . 42   
3.3.6 A600: Environmental and Operational requirements [OpR] . 42   
3.3.7 A700: Safety requirements [SafR]. .. 43   
3.3.8 A800: Configuration and implementation requirements [ConfR] . 43   
3.4 Walking Manipulator Requirements [Bxxx] 45   
3.4.1 B100: Functional requirements [FuncR] 45   
3.4.2 B200: Performance requirements [PerfR] . 47   
3.4.3 B300: Interface requirements [IntR] . 48   
3.4.4 B400: Design requirements [DesR]. . 50

## MOSAR - System Requirements Document

3.4.5 B500: Physical and resource requirements [PhyR]. . 52   
3.4.6 B600: Environmental and Operational requirements [OpR] . 52   
3.4.7 B700: Safety requirements [SafR] .. 52   
3.4.8 B800: Configuration and implementation requirements [ConfR] . 52   
3.5 Spacecraft Modules Requirements [Cxxx] . . 53   
3.5.1 C100: Functional requirements [FuncR] . 53   
3.5.2 C200: Performance requirements [PerfR] .. 55   
3.5.3 C300: Interface requirements [IntR] . 56   
3.5.4 C400: Design requirements [DesR]. . 57   
3.5.5 C500: Physical and resource requirements [PhyR]. .. 60   
3.5.6 C600: Environmental and Operational requirements [OpR]. . 61   
3.5.7 C700: Safety requirements [SafR]. .. 61   
3.5.8 C800: Configuration and implementation requirements [ConfR]. .. 61   
3.6 Standard Interfaces Requirements [Dxxx] .. 62   
3.6.1 D100: Functional requirements [FuncR] . 62   
3.6.2 D200: Performance requirements [PerfR] . 64   
3.6.3 D300: Interface requirements [IntR] .. 66   
3.6.4 D400: Design requirements [DesR]. .. 67   
3.6.5 D500: Physical requirements [PhyR]. . 68   
3.6.6 D600: Environmental and Operational requirements [OpR]. . 69   
3.6.7 D700: Safety requirements [SafR]. .. 70   
3.6.8 D800: Configuration and implementation requirements [ConfR]. .. 70   
3.7 Planner and Simulator Requirements [Exxx] ... 71   
3.7.1 E100: Functional requirements [FuncR]. ... 71   
3.7.2 D200: Performance requirements [PerfR] . 73   
3.7.3 D300: Interface requirements [IntR] .. 73   
3.7.4 D400: Design requirements [DesR]. .. 74   
3.7.5 D500: Physical and resource requirements [PhyR]. .. 75   
3.7.6 D600: Environmental and Operational requirements [OpR]. . 75   
3.7.7 D700: Safety requirements [SafR]. . 75   
3.7.8 D800: Configuration and implementation requirements [ConfR]. . 75   
3.8 Software Requirements [Fxxx] . 76   
3.8.1 F100: Functional requirements [FuncR] .. 76   
3.8.2 F200: Performance requirements [PerfR] .. 77   
3.8.3 F300: Interface requirements [IntR]. .. 78   
3.8.4 F400: Design requirements [DesR] . 78

## MOSAR - System Requirements Document

3.8.5 F500: Physical and resource requirements [PhyR] . . 78   
3.8.6 F600: Environmental and Operational requirements [OpR] . . 78   
3.8.7 F700: Safety requirements [SafR] . . 78   
3.8.8 F800: Configuration and implementation requirements [ConfR] . . 79   
3.9 Validation Requirements [Gxxx]. . 80   
4 Conclusions . 83

## MOSAR - System Requirements Document

## List of Figures

Figure 2-1 - Schematic view of a MOSAR-like mission... .. 11   
Figure 3-1: MOSAR Demonstrator Concept.... ..... 31

## MOSAR - System Requirements Document

## List of Tables

Table 1: Example of requirement .. .... 12   
Table 2: Example of requirement ...... ..... 32

## 1 Introduction

## 1.1 Purpose and Scope

The purpose of this document is to provide the system requirements for MOSAR that are derived from the from the SRC Compendium document, the analysis of the modular spacecraft applications and relevant technology review (including previous OGs building blocks), the MOSAR operational concept and the demonstration scenarios.

The document is mainly divided in two parts. The first part addresses the extraction of requirements associated with future space mission scenarios of modular spacecraft applications. They are mainly derived from the analysis of the most promising use cases of On-orbit reconfiguration and the associated technological needs (RD2-D1.2). These requirements are considered as guidelines for the development of the MOSAR demonstrator, to target a good representativeness of future missions.

The second part addresses more specifically the technical requirements of the MOSAR demonstrator that will be designed, developed and tested during this activity. The requirements are described at system level, for each of the main sub-systems and for the validation phase.

## 1.2 Document Structure

This document is structured as follows:

Section 1 Introduction

Section 2 Modular Spacecraft Requirements

Section 3 MOSAR Demonstrator Requirements

## 1.3 Applicable Documents

AD1 SRC – Guidance Document for H2020 Work Programe 2018-2020 (SPACE-12-TEC-2018)

AD2 MOSAR Consortium Agreement, version 1.0 (7<sup>th</sup> November 2018)

AD3 MOSAR Grant Agreement (821996) (18<sup>th</sup> January 2019)

AD4 MOSAR Proposal; H2020-SPACE-2018-2020 (SEP-210504862)

## 1.4 Reference Documents

RD1 MOSAR-WP1-D1.1-GMV OG1-5 Building Block Update Documentation Package

RD2 MOSAR-WP1-D1.2-TASF Report on MOSAR Applicable Technologies Review

RD3 MOSAR-WP1-D1.3-DLR Operational Concept

## 1.5 Acronyms

<table><tr><td>APM</td><td>Active Payload Module</td></tr><tr><td>ASM</td><td>Active System Module</td></tr><tr><td>CAN</td><td>Controller Area Network</td></tr><tr><td>CLT</td><td>Client (spacecraft)</td></tr><tr><td>DDS</td><td>Data Distribution Service</td></tr><tr><td>ERGO</td><td>European Robotic Goal-Oriented Autonomous Controller</td></tr><tr><td>ESA</td><td>European Space Agency</td></tr><tr><td>ESROCOS</td><td>European Space Robotics Control and Operating System</td></tr><tr><td>FES</td><td>Functional Engineering Simulator</td></tr><tr><td>FM</td><td>Functional Module</td></tr><tr><td>GEO</td><td>Geostationary Earth Orbit</td></tr><tr><td>GTO</td><td>Geostationary Transfer Orbit</td></tr><tr><td>I3DS</td><td>Integrated 3D Sensors</td></tr><tr><td>InFuse</td><td>Infusing Data Fusion in Space Robotics</td></tr><tr><td>LEO MCC</td><td>Low Earth Orbit</td></tr><tr><td>MOSAR</td><td>Monitoring and Control Center</td></tr><tr><td>OBC</td><td>Modular Spacecraft Assembly and Reconfiguration On-Board Computer</td></tr><tr><td>OG</td><td>Operational Grant</td></tr><tr><td>PERASPERA</td><td>Plan the European Roadmap and its Activities for Space Exploitation of Robotics and</td></tr><tr><td>PUS</td><td>Autonomy Packet Utilization Standard</td></tr><tr><td>R-ICU</td><td>Reduced Instrument Control Unit</td></tr><tr><td>SI</td><td>Standard Interface</td></tr><tr><td>SIROM</td><td>Standard Interface for Robotic Manipulation of Payloads in Future Space Missions</td></tr><tr><td>SM</td><td></td></tr><tr><td></td><td>Spacecraft Modules</td></tr><tr><td>SpW</td><td>SpaceWire</td></tr><tr><td>SRC</td><td>Strategic Research Cluster</td></tr><tr><td>SVC</td><td>Servicer (spacecraft)</td></tr><tr><td>TASTE</td><td>The ASSERT Set of Tools for Engineering</td></tr><tr><td>TBC</td><td>To be Confirmed</td></tr><tr><td>TBD</td><td>To be Defined</td></tr><tr><td>TC</td><td>Telecommand</td></tr><tr><td>TM</td><td>Telemetry</td></tr><tr><td>WM</td><td>Walking Manipulator</td></tr></table>

## 2 Modular Spacecraft Requirements

## 2.1 Mission Overview

The selection of the MOSAR space mission application has to be done in perspective with the other space mission applications selected for PULSAR and for EROSS:

PULSAR space mission will consist in assembling a large telescope at Earth-Sun L2 point using a robotic manipulator, with all the telescope and platform elements packaged in a single launch.

EROSS space mission will consist in the in-space servicing of a LEO satellite, with refueling and units replacement, using state-of-the-art robotic arm and equipment.

Following the analysis of RD2, a mission concept is proposed that exploits at best the benefits of the modular approach, that is realistically feasible in the short/mid-term and that is commercially oriented towards the reduction of costs and the maximization of profit.

The proposed MOSAR space mission application consists in upgrading, reconfiguring and repairing an operational GEO telecommunication satellite.

The satellite, in its original configuration, will have an initial telecommunication payload capacity and will be assembled and tested on-ground, but it will feature key design concepts to meet the mission objective:

## Modular design:

The satellite original configuration will be based on the conventional all-integrated platform, but will feature some specific modules, removable from the outside of the satellite, dedicated to power generation (solar array + power conditioning) and payloads.

## Scalable design:

The satellite original configuration will allow in-space connection of additional modules through standard interfaces at the outside of the satellite.

The mission is divided into 3 different phases:

## Phase 1: launch of satellite with initial capacity

The satellite is assembled and tested on-ground and is launched fully integrated into a GTO. The satellite then uses its own propulsion system to raise its orbit to reach its GEO position slot.

After in-orbit tests and commissioning, the satellite is capable to deliver an initial capacity (e.g. high throughput internet connection).

## Phase 2: capacity increase + upgrade of payload + addition of hosted payload

After several years in-orbit (approximately 5 years), there is a need coming from the market to upgrade the payload (removal of obsolete technologies) and to add telecommunication capacity to the existing satellite, while also adding an hosted payload for meteorology on the Earth pointing panel to increase financial revenues and profitability.

Dedicated modules (power generation module, payload modules, hosted payload module) will be manufactured, tested on-ground and launched into GTO (can be a co-passenger with another GEO satellite). A servicer equipped with a robotic arm and positioned near the GTO injection point, will then capture the modules, bring them to the satellite operational orbit (i.e. perform an orbit raising and insertion into GEO slot of its client) where it will assemble them with the following sequence:

o Addition of power generation module and in-orbit tests for verification of performances

o Removal and storage of obsolete payload modules

o Replacement of obsolete payload modules and in-orbit tests for verification of performances

o Addition of telecommunication payload modules and in-orbit tests for verification of performances

o Addition of hosted payload module and in-orbit tests for verification of performances

## Phase 3: replacement of failed battery + addition of deorbiting propulsion kit

After additional years of operations, failure of parts subjected to ageing (e.g. battery, thrusters) occurred preventing the satellite from operating nominally and performing specific station keeping maneuvers (e.g. E/W or N/S).

Dedicated modules (battery module, propulsion kit) are manufactured, tested on-ground and launched as co-passenger to another GTO mission. As for Phase 2, a servicer will capture and bring them to the satellite operational orbit and perform the modules exchange.

![](images/1f17cb967eca45ebf84ac3220195621780253137d7f33c224068e36fc7ca98f5.jpg)  
Figure 2-1 - Schematic view of a MOSAR-like mission.

This mission concept is proposed as an example, to guide the development of the demonstrator.   
However it should not limit in any way the applicability of MOSAR to any other kind of mission.

MOSAR is a project aiming at demonstrating a set of key technologies that are considered essential for the development of future applications of On-Orbit Servicing and On-Orbit Assembly. The objectives of MOSAR include (AD3):

Review, extension and integration of common robotic building blocks: ESROCOS, ERGO and InFuse software building blocks; I3DS perception suite and SIROM standard interface.

Development of a repositionable walking manipulator, enabling a cost-effective solution for actuation on a wide workspace without escalation of size and performance of the robot.

Elaboration of a concept for modular spacecraft: identifying key design choices and highlighting recommendations for development of standards for design and operation of future modular space vehicles.

The first two objectives should be generic and independent from any specific mission, as the final purpose is to develop a standard that is unique and re-usable across different missions. As for the third objective, the applicability of the modular approach to different missions is discussed in RD2, highlighting the main advantages that modularity would bring to specific applications and the main design and operation requirement that would need to be fulfilled.

## 2.2 Space Scenarios Requirements

MOSAR does not target a specific mission in particular, but rather aims at demonstrating key functionalities that are intended to be generic and applicable to very different scenarios. Therefore, it has been preferred not to restrain MOSAR applicability to a given mission, but to present general requirements that can be common to multiple missions. These requirements are not expected to be fully verified in the context of the current project. They should be considered as guidelines for the developments in the current activity to favor compatibility with future mission goals and requirements.

## 2.2.1 Formalism

The following section details the space scenarios requirements following the structure exemplified in this table:

Table 1: Example of requirement
<table><tr><td>YY_uniquelD</td><td>Title</td><td>LEVEL</td></tr><tr><td>STATEMENT</td><td>Requirement Statement</td><td></td></tr><tr><td>COVERS</td><td>Origin</td><td></td></tr><tr><td>COMMENT</td><td>Additional comment and explanations</td><td></td></tr></table>

The top row of the table includes:

● Unique ID: identificator with the structure YY\_uniqueID

○ YY: type of the requirement - Functional requirements (FuncR), Performance requirements (PerfR), Interface requirements (IntR), …

○ uniqueID: unique reference with 4 characters:

■ The first character is a “S”, for Space Scenarios Requirements

■ The next number identifies the type of requirement inside the subsystem

■ The next two numbers identify a number assigned to each requirement in that category

● Title: highlighting the topic of the requirement

● LEVEL: indicates the level of importance of the requirement (mandatory / desirable / optional) The rest of the table includes the following fields:

● STATEMENT: clear and concise description of the requirement

COVERS: gives indication about the origin/scope of the requirements (specific user requirement or user case, partner expertise, project constraint, etc.)

● COMMENT: provides rationale or additional comments about the requirement

## 2.2.2 S100: Functional requirements [FuncR]

<table><tr><td rowspan=1 colspan=1>FuncR_S101</td><td rowspan=1 colspan=1>Satellite repair and update</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The MOSAR technology shall allow repair and update of modular spacecraft bymanipulation and repositioning of functional modules with a robotic manipulator</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2Guidelines AD1-OG9-R02</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_S102</td><td rowspan=1 colspan=1>Mission tasks update</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The modular spacecraft shall be reconfigurable and should be able to use newfunctionalities brought by additional functional modules, in order to perform new missiontasks</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2Guidelines AD1-OG9-R05</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_S103</td><td rowspan=1 colspan=1>Functional modules replacement</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The robotic manipulator shall be able to add and replace whole functional modules(ASM/APM) by using the interconnectors of these modules.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2Guidelines AD1-OG9-R01</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td>FuncR_S104</td><td>Robot relocation</td><td>Mandatory</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=1>The robotic manipulator shall be able to reposition itself by using theinterconnectors/structure of the functional modules or the spacecraft</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Mission analysis RD2Guidelines AD1-OG9-R03</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=1></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_S105</td><td rowspan=1 colspan=1>Design software</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>A design software shall be able to create a robotic compatible servicing / reconfigurationplan for the modular spacecraft</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Operational Concept RD3Guidelines AD1-OG9-R12</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_S106</td><td rowspan=1 colspan=1>Simulation software</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>A simulation software shall be able to simulate the system with all related roboticselements following the execution plan</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Operational Concept RD3Guidelines AD1-OG9-R12</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>FuncR_S107</td><td rowspan=1 colspan=1>Robot high-level control</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The modular spacecraft shall perform the high-level control of the robot, by theexecution and monitoring of the reconfiguration plan (task level)</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Operational Concept RD3Guidelines AD1-OG9-R04</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>The high-level control of the robot can also be managed by the servicer satellite(depending on the servicing or local reconfiguration scenario)</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_S108</td><td rowspan=1 colspan=1>Robot low-level control</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The robotic manipulator shall ensure its low-level control for the execution of the high-level tasks</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Operational Concept RD3Guidelines AD1-OG9-R04</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR S109</td><td rowspan=1 colspan=1>Functional module monitoring</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The modular spacecraft shall be able to monitor the status of essential parameters ofeach connected functional module</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2Guidelines AD1-OG9-R12</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_S110</td><td rowspan=1 colspan=1>Resources reallocation</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The system shall be able to reallocate resources (e.g. power, data, computationalpower, etc.) and assign different path automatically in case of a defect (e.g.interconnector of an APM)</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2Guidelines AD1-OG9-R07</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td>FuncR_S111</td><td>Failure handling</td><td>Mandatory</td></tr><tr><td>STATEMENT</td><td>The system shall be able to handle the tasks even during a connection failure or a power interruption of defect modules/interconnectors.</td><td></td></tr><tr><td>COVERS</td><td>Mission analysis RD2 Guidelines AD1-OG9-R08</td><td></td></tr><tr><td>COMMENT</td><td></td><td></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_S112</td><td rowspan=1 colspan=1>Electrical power supply</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>One or several modules options shall be available to implement for electrical powersupply enabling operation of the functional modules and the robot manipulator</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>The power system could be integrated by one or more functional modules</td></tr></table>

<table><tr><td>FuncR_S113</td><td>Electrical power supply, power management</td><td>Mandatory</td></tr><tr><td>STATEMENT</td><td>The modular spacecraft shall be able to shut down or command a stand-by mode of any non-critical module to reduce power consumption if needed. Critical functions should not be affected by shutting down of non-critical modules.</td><td></td></tr><tr><td>COVERS</td><td>Mission analysis RD2</td><td></td></tr><tr><td>COMMENT</td><td></td><td></td></tr></table>

<table><tr><td>FuncR S114</td><td>Data handling system</td><td>Mandatory</td></tr><tr><td>STATEMENT</td><td>One or several modules options shall be available to implement a data handling system (that can be composed of one or more modules) that enables operation of the different modules and the manipulator.</td><td></td></tr><tr><td>COVERS</td><td>Mission analysis RD2</td><td></td></tr><tr><td>COMMENT</td><td>The data handling system could be integrated by one or more functional modules</td><td></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>FuncR_S115</td><td rowspan=1 colspan=1>Heat management and thermal considerations</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>One or several modules options shall be available to implement heat managementfunctions that allow thermal regulation of the different modules within its specific rangeof temperatures. The heat management system could be composed of one or moremodules.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_S116</td><td rowspan=1 colspan=1>Propulsion subsystem</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>One or several modules options shall be available to implement a propulsion subsystemwith capacity to perform at least:Station keeping manoeuvers.Orbit relocation.De-orbiting.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>The propulsion subsystem could be integrated by one or more functional modules.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_S117</td><td rowspan=1 colspan=1>Attitude control subsystem</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>One or several modules options shall be available to implement an attitude controlsubsystem, with capacity to perform at least:Spacecraft reorientation.Attitude control compatible with mission objectives.Autonomous search of the Sun and the Earth</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>The attitude control subsystem is essential to ensure correct functioning of othersubsystems.</td></tr></table>

<table><tr><td>FuncR_S118</td><td>Module mechanical connections</td><td>Mandatory</td></tr><tr><td>STATEMENT</td><td>Modules shall be able to connect mechanically to other modules or to the spacecraft through interconnectors.</td><td></td></tr><tr><td>COVERS</td><td>Mission analysis RD2</td><td></td></tr><tr><td>COMMENT</td><td>Not every module is directly linked to the OBC of the modular platform. Data relay function is needed to dispatch telecommands and telemetries through a network of modules.</td><td></td></tr></table>

<table><tr><td>FuncR_S119</td><td colspan="5">Module data relay Mandatory</td></tr><tr><td>STATEMENT</td><td colspan="5">Any module should be able to act as a data relay for other modules or the robotic manipulator through their interconnector, also if the module is in safe mode</td></tr><tr><td>COVERS</td><td colspan="5">Mission analysis RD2</td></tr><tr><td>COMMENT</td><td colspan="5">Not every module is directly linked to the OBC of the modular platform. Data relay function is needed to dispatch telecommands and telemetries through a network of modules.</td></tr><tr><td rowspan="7"></td><td colspan="5"></td></tr><tr><td></td><td><img src="images/23563d121ff82aac041eb76ce0a3b6d5f90d3c0ab7eb50bc4f7498fe20709a80.jpg"/></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td></tr><tr><td>FM1 is in safe mode but still acts as data relay for FM2.</td><td></td><td></td><td></td></tr><tr><td></td><td></td><td><img src="images/45fc48022f4dc66e5e68d94bf05dbd8fee7d25d9e087d78906f149f990e5c662.jpg"/></td><td></td></tr><tr><td></td><td></td><td></td><td></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_S120</td><td rowspan=1 colspan=1>Data routing</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The OBC shall be able to redirect telecommands to specific modules, for the spacecraftconfiguration or for instance upon detection of failure on any point of the network.If an alternative path is not available, the OBC shall be able to isolate the faulty nodeand all the others nodes connected downstream.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>FM5 has a nominal link to the OBC through FM3 and FM4. In case of failure of any ofthese components, the OBC should redirect telecommands to FM5 through the alternativepath using FM1 and FM2.</td></tr></table>

![](images/97ca3a6ec7b332f420d99a49394da6ffa3bd062205eb0328f6eb0c2a1daec242.jpg)

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>FuncR_S121</td><td rowspan=1 colspan=1>Module power relay</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>Module should be able to act as a power relay for other modules or the roboticmanipulator through their interconnectors, also if the module is in safe mode</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2FuncR_S112</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>To allow power distribution between the power supply (spacecraft or functional module)and the other active modules</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_S122</td><td rowspan=1 colspan=1>Power routing</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The OBC shall be able to redirect power to specific modules, for the spacecraftconfiguration or for instance upon detection of power failure on any point of the network.If an alternative path is not available, the OBC shall be able to isolate the faulty nodeand all the others nodes connected downstream.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>To allow power distribution between the power supply (spacecraft or functional module)and the other active modules</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>FuncR_S123</td><td rowspan=1 colspan=1>Module thermal relay</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>Module should be able to act as a thermal relay for other modules through theirinterconnectors</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2FuncR_S115</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>To allow thermal distribution and management between the modules</td></tr></table>

## 2.2.3 S200: Performance requirements [PerfR]

Performance requirements are specific to each application. Detailed mission analysis is needed to adapt the generic requirements presented hereafter to the specific need of the mission.

<table><tr><td>PerfR_S201</td><td>Mechanical interfaces</td><td>Mandatory</td></tr><tr><td>STATEMENT</td><td>The modular spacecraft shall be able to withstand the loads expected on orbit with significant (TBD) safety margins. In any case, the mechanical integrity of the ensemble should not be compromised.</td><td></td></tr><tr><td>COVERS</td><td>Mission analysis RD2</td><td></td></tr><tr><td>COMMENT</td><td></td><td></td></tr></table>

<table><tr><td rowspan=1 colspan=1>PerfR_S202</td><td rowspan=1 colspan=1>Manipulator mechanical loads</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The robot manipulator and its connections to the modules or spacecraft shall be able towithstand the loads expected during modules operations with significant (TBC) safetymargins.In any case, the mechanical integrity of the robotic arm and its connection with thespacecraft or modules should not be compromised.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td rowspan=1 colspan=1>PerfR_S203</td><td rowspan=1 colspan=1>Mechanical interfaces (alignment and stiffness)</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The mechanical interfaces of the modular spacecraft shall provide the requiredalignment accuracy and stiffness required by the different modules to meet theirrespective performance requirements and to not constitute a harm to the rest of thespacecraft.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>The performance requirements of the different modules could be treated at systemlevel, showing adequacy to the mission objectives.The minimum need in terms of alignment and stiffness of the mechanical interfaceshould at least guarantee that every module is safely integrated into the modularplatform.</td></tr></table>

## MOSAR - System Requirements Document

2.2.4 S300: Interface requirements [IntRD]
<table><tr><td rowspan=1 colspan=1>IntR_S301</td><td rowspan=1 colspan=1>Ground segment communication</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The modular spacecraft shall have a redundant communication link with the groundsegment for telemetry and telecommands.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_S302</td><td rowspan=1 colspan=1>Telemetry of different modules</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>Every module shall have a communication link enabling to send telemetry to thespacecraft monitoring unit (OBC) and ultimately to the ground station. The link with theground station could be done through a specific communication module implemented onthe modular spacecraft</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_S303</td><td rowspan=1 colspan=1>Ground segment surveillance</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The ground segment shall know at any moment the status of the different modules ofthe modular spacecraft. This information is passed through two types of telemetries:Periodic telemetry with standardized packets.Asynchronous telemetry with error message.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>The ground segment is able to detect problems in case an anomaly message isreceived (asynchronous telemetry). Even if the error message is never received (forinstance, sudden power loss), the ground segment is able to detect a problem if theperiodic telemetry is not received and investigate the problem by analyzing this data.</td></tr></table>

<table><tr><td>IntR_S304</td><td>Grounding (electrical power)</td><td>Mandatory</td></tr><tr><td>STATEMENT</td><td>Any module of the modular spacecraft provided with an electrical power interface should have a connection to ground.</td><td></td></tr><tr><td>COVERS</td><td>Mission analysis RD2</td><td></td></tr><tr><td>COMMENT</td><td>Reduces the risk of introducing stray currents or ground loop currents.</td><td></td></tr></table>

## MOSAR - System Requirements Document

2.2.5 S400: Design requirements [DesR]
<table><tr><td>DesR_S401</td><td>Modular satellite reliability</td><td>Desirable</td></tr><tr><td>STATEMENT</td><td>The modular spacecraft shall be quantifiably more reliable by design than a monolithic system over the mission lifetime of the satellite, including (and as a specific advantage) under extensions of mission lifetime.</td><td></td></tr><tr><td>COVERS</td><td>Mission analysis RD2</td><td></td></tr><tr><td>COMMENT</td><td></td><td></td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_S402</td><td rowspan=1 colspan=1>Modular satellite flexibility</td><td rowspan=1 colspan=1>Desirable</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The modular spacecraft shall be quantifiably more flexible in operation and responsiveto mission changes than a traditional satellite with a similar mission.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_S403</td><td rowspan=1 colspan=1>Modular satellite economy</td><td rowspan=1 colspan=1>Desirable</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The modular spacecraft shall have quantifiable advantages in cost-effectiveness andeconomy of operation from a mission perspective over the projected lifetime of thesatellite.Otherwise, it should be demonstrated that the benefits (in terms of enhancedfunctionalities) compensate the additional costs.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_S404</td><td rowspan=1 colspan=1>Available connection interfaces</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The modular spacecraft and modules assembly shall implement a minimum number ofconnection interfaces such as at least two of these interfaces are available at anymoment and within the reach of the robotic manipulator.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>one spot for anchorage on the client spacecraft and a second one for placing a newmodule.</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td>DesR_S405</td><td>Compatibility between modules</td><td>Mandatory</td></tr><tr><td>STATEMENT</td><td>The assembly of modules on a modular spacecraft respond to a planning and design that has previously being verified on ground.</td><td></td></tr><tr><td>COVERS</td><td>Mission analysis RD2</td><td></td></tr><tr><td>COMMENT</td><td></td><td></td></tr></table>

## 2.2.6 S500: Physical and resource requirements [PhyR]

<table><tr><td rowspan=1 colspan=1>PhyR_S501</td><td rowspan=1 colspan=1>Components weight</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The weight of all components associated with the concept of modular spacecraft shallbe minimized (interconnectors, functional module structure, robotic manipulator)</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>The concept of modular spacecraft brings additional components that creates a penaltyon the system weight.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>PhyR_S502</td><td rowspan=1 colspan=1>Interconnectors size and volume</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The size and volume of the interconnectors shall be minimized to offer more placeinside the functional modules</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

## 2.2.7 S600: Environmental and Operational requirements [OpR]

<table><tr><td rowspan=1 colspan=1>OpR_S601</td><td rowspan=1 colspan=1>Servicer satellite</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The functional modules shall be delivered to the modular spacecraft by a servicersatellite equipped with a robotic manipulator</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>OpR_S602</td><td rowspan=1 colspan=1>On-Orbit Rendez-vous, interfaces</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The modular spacecraft shall implement a physical interface for docking and/or berthingof a servicer satellite.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td rowspan=1 colspan=1>OpR_S603</td><td rowspan=1 colspan=1>On-Orbit Rendez-vous, coupled spacecraft</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The modular spacecraft shall be able to remain coupled to the servicer spacecraftwithout time limitation.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>There should be no limitation coming from any of the subsystems of the modularspacecraft (ADCS, power, thermal etc.).</td></tr></table>

<table><tr><td rowspan=1 colspan=1>OpR_S604</td><td rowspan=1 colspan=1>On-Orbit Rendez-vous, communication to servicer</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The modular spacecraft should be able to communicate with the servicer and exchangedata during and after rendez-vous operation.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>Not essential during rendez-vous but highly desirable for enhanced autonomy duringoperations without (or with minimum) ground support.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>OpR_S605</td><td rowspan=1 colspan=1>On-Orbit Rendez-vous, ground communications</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The modular spacecraft shall be able to monitor operations during and after rendez-vous and send reports to the ground segment.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>Continuous link to ground stations is not essential for rendez-vous, however, differentphases are usually defined with specific milestones that are controlled by groundoperators.After rendez-vous, the communication supports transfer of the execution plan and themonitoring and feedback of the operations to the ground.</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td>OpR_S606</td><td>Space environment</td><td>Mandatory</td></tr><tr><td>STATEMENT</td><td>The components of the modular spacecraft: subsystems, interfaces and structures shall be able to withstand the space environment for the whole duration of the mission.</td><td></td></tr><tr><td>COVERS</td><td>Mission analysis RD2</td><td></td></tr><tr><td>COMMENT</td><td>Generic requirement to be verified depending on the specific application.</td><td></td></tr></table>

<table><tr><td rowspan=1 colspan=1>OpR_S607</td><td rowspan=1 colspan=1>Launch loads</td><td rowspan=1 colspan=1>Desirable</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The interconnectors design shall optimize launch load capabilities, to offer the widerrange of possibilities regarding pre-assembled functional modules (on the initialspacecraft or the servicer) before launch</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>Conditions are function of the launch conditions, configuration of the modules (inertia,COG,...) and type of connection with the launcher</td></tr></table>

2.2.8 S700: Safety requirements [SafR]
<table><tr><td rowspan=1 colspan=1>SafR_S701</td><td rowspan=1 colspan=1>Critical functionalities</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The failure of any functional module shall not yield to the loss of the spacecraft.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td rowspan=1 colspan=1>SafR_S702</td><td rowspan=1 colspan=1>Redundancy of critical functionalities</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>Any functional module providing a critical functionality (one that is needed for the safemode of the functional platform) shall be redundant.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td>SafR_S703</td><td>Propagation of failures</td><td>Mandatory</td></tr><tr><td>STATEMENT</td><td>Any module of the modular spacecraft shall be designed as to avoid failure propagation. In particular, the module shall prevent itself or any of its components from degrading performances of other modules or damaging the modular spacecraft.</td><td></td></tr><tr><td>COVERS</td><td>Mission analysis RD2</td><td></td></tr><tr><td>COMMENT</td><td></td><td></td></tr></table>

<table><tr><td rowspan=1 colspan=1>SafR_S704</td><td rowspan=1 colspan=1>Substitution of critical modules</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>Any module that is considered critical (without this module the spacecraft loss one of itsbasic functionalities) can only be exchanged if:1. Another module covering its functionality has already been added to the clientspacecraft.2. This second module is already operational.3. The module to be substituted has already been isolated and switched off.4. No anomaly has been detected between steps 2 and 3.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>The design principle of “do not harm” should be applied for the modules of a modularspacecraft.</td></tr></table>

<table><tr><td>SafR_S705</td><td colspan="6">Robustness to power loss Mandatory</td></tr><tr><td>STATEMENT</td><td colspan="6">Any module shall be able to withstand a sudden power loss without any damage to itself or to other modules. The module shall autonomously shut down or enter a standby mode of minimum power consumption.</td></tr><tr><td>COVERS</td><td colspan="6">Mission analysis RD2</td></tr><tr><td>COMMENT</td><td colspan="6">The design principle of “do not harm” should be applied for the modules of a modular spacecraft. In case of major anomaly of FM1, FM2 may suddenly lose its power supply.</td></tr><tr><td rowspan="2"></td><td rowspan="2"></td><td rowspan="2">Power</td><td rowspan="2">FM1</td><td rowspan="2"></td><td rowspan="2">FM2</td></tr><tr><td rowspan="2"></td></tr><tr><td></td><td></td><td>E</td><td>才</td><td>V</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td>SafR_S706</td><td colspan="5">Restart after power loss Mandatory</td></tr><tr><td>STATEMENT</td><td colspan="5">After a sudden power loss, any module of the modular spacecraft shall be able to restart and resume normal operation when power supply is restored.</td></tr><tr><td>COVERS</td><td colspan="5">Mission analysis RD2</td></tr><tr><td>COMMENT</td><td colspan="5">The design principle of “do not harm” should be applied for the modules of a modular spacecraft. When functionality of FM1 is restored, the modules downstream (FM2) can restart and resume normal operation.</td></tr><tr><td rowspan="3"></td><td rowspan="3">Power</td><td colspan="2"></td><td></td></tr><tr><td><img src="images/68af9b6222eab6cc8310da2743473e4cd3e639f6803f014d14e6710e9ec41099.jpg"/></td><td>V <img src="images/bee73f979277c560a6bc7cee13d5a49aa2640e7503d2640fa83186f9fe64f4bb.jpg"/></td><td></td></tr><tr><td colspan="3"></td></tr></table>

<table><tr><td rowspan=1 colspan=1>SafR_S707</td><td rowspan=1 colspan=1>Data handling system (redundancy)</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The modular spacecraft shall implement a redundant on-board computer. The two (ormore) OBCs could be integrated in different modules or in the same module. If theOBCs are integrated in the same module, two different interfaces should be provided,ensuring that in any case a single failure does not yield to the loss of the spacecraft.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td rowspan=1 colspan=1>SafR_S708</td><td rowspan=1 colspan=1>Modular Satellite Failure Detection, Isolation and Recovery</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The modular satellite shall be able to detect failure of any module, isolate the faultyequipment and perform recovery operations when possible</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td>SafR_S709</td><td>Safe mode</td><td>Mandatory</td></tr><tr><td>STATEMENT</td><td>The modular spacecraft shall implement a safe mode that guarantees a stable condition of the spacecraft without time limitation. This mode should be fully autonomous (without any ground intervention).</td><td></td></tr><tr><td>COVERS</td><td>Mission analysis RD2</td><td></td></tr><tr><td>COMMENT</td><td></td><td></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>SafR_S710</td><td rowspan=1 colspan=1>Safe mode (modules)</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>Any module of the modular spacecraft shall implement a safe mode. This modeminimizes hardware and software functions as to make minimal use of the modularspacecraft resources (power).</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td rowspan=1 colspan=1>SafR_S711</td><td rowspan=1 colspan=1>Safe mode (command)</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The modular spacecraft should enter safe mode either by autonomous transitiontriggered by the on-board computer or through ground command.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td>SafR_S712</td><td>Safe mode (modules, command)</td><td>Mandatory</td></tr><tr><td>STATEMENT</td><td>Any module of the modular spacecraft should enter in safe mode when commanded by the on-board computer of the modular spacecraft, by ground command or by autonomous triggering of the module itself.</td><td></td></tr><tr><td>COVERS</td><td>Mission analysis RD2</td><td></td></tr><tr><td>COMMENT</td><td></td><td></td></tr></table>

<table><tr><td rowspan=1 colspan=1>SafR_S713</td><td rowspan=1 colspan=1>Data relay for critical modules</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>Any module considered as critical (needed for the safe mode of the modular platform,ensuring no loss of the spacecraft) shall have either:a) A direct connection to the OBC.b) Two independent paths to reach the OBC through other modules.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2Guidelines AD1-OG9-R07</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>FM1 and FM5 are critical modules. FM1 is directly connected to the OBC. FM5 is notdirectly connected to the OBC, but has two alternative ways of communicating with theOBC. The design is robust to a single failure of any of the non-critical modules.</td></tr></table>

## MOSAR - System Requirements Document

![](images/6cfa4919a62d7b7c713dcb5bedb1773a44c25342bebe4af7ed84b5f833416e1d.jpg)

<table><tr><td rowspan=1 colspan=1>SafR_S714</td><td rowspan=1 colspan=1>Power relay for critical modules</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>Any module considered as critical (needed for the safe mode of the modular platform,ensuring no loss of the spacecraft) shall have either:a) A direct connection to the power supply.b) Two independent paths to reach the power supply through other modules.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

<table><tr><td rowspan=1 colspan=1>SafR_S715</td><td rowspan=1 colspan=1>Single points of failure</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The design of the modular spacecraft shall minimize the number of single point offailures (failure that yields to loss of the spacecraft or its mission). Every single point offailure should be fully described, analyzed, and justified why any other implementation isnot better than the selected one</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2></td></tr></table>

2.2.9 S800: Configuration and implementation requirements [ConfR]
<table><tr><td rowspan=1 colspan=1>ConfR_S801</td><td rowspan=1 colspan=1>Configuration of the modular spacecraft</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>A modular spacecraft implements identical modules in terms of structure shape andmaterials. Singularly, different shapes could be accepted provided that compatibility withthe basic modules is ensured.</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>The basic module is the rectangle. Singularly, other modules that are compatible could</td></tr></table>

## MOSAR - System Requirements Document

![](images/b65b8d61c781503447e801ae2ef49502c2ac3e5b5077cc018b152d37df57f4ff.jpg)

<table><tr><td rowspan=1 colspan=1>ConfR_S802</td><td rowspan=1 colspan=1>Functional module orientation</td><td rowspan=1 colspan=1>Mandatory</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=2>The functional module orientation shall be adjustable as function of its function andposition on the modular spacecraft</td></tr><tr><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=2>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=2>The function of the module could require a specific orientation (e.g. camera orientation,radiator)</td></tr></table>

## 3 MOSAR Demonstrator Requirements

## 3.1 Demonstrator Overview

The purpose of the MOSAR demonstrator is to illustrate scenarios of modular spacecraft assembly and re-configuration operations. The baseline scenario is the one of a Servicer Spacecraft (SVC) transporting a cargo of Spacecraft Modules (SM) and a dedicated Walking Manipulator (WM), performing a number of operations with the transfer of SM from and to the Client Spacecraft (CLT) by the manipulator.

![](images/c0bbc9d44e20a844d56e6fe306ece637c7acbd7f35009bc03536d32d39fccec6.jpg)  
Figure 3-1: MOSAR Demonstrator Concept

Spacecraft Modules are individual structures associated with a specific function of the spacecraft, that once assembled, will ensure the spacecraft operations. They can cover system (ASM, Active System Modules) or payload (APM, Active Payload Modules) functions. The SM are equipped with Standard Interfaces (SI) enabling Modules to Modules and Modules to spacecraft connections. Each SI provides mechanical, data, power and thermal transfer capabilities, allowing a full configuration of the CLT functions. That includes mechanical structural integrity, data transmission, power routing and thermal management along the elements.

The main purpose of the manipulator is to transfer the SM between the servicer and the client satellite. In order to answer the problem of reachability, the MOSAR concept is based on the implementation of a walking manipulator that ensures a high mobility along the structure. Equipped with Standard Interfaces at its both end-effectors, it can attach and manipulate the SM, but also move along the structure by connection to either the SM or the spacecraft SI. The connection is also used to power the arm and transfer the control commands coming from the spacecraft computer.

The autonomous transfer and configuration of the SM follow an execution plan prepared and validated off-line, in the Monitoring and Control Centre (MCC), on the ground segment. The MCC includes a satellite design, modelling and validation tool, specifically targeting modular satellites applications. It also allows the automatic planning of the assembly or reconfiguration sequence that can be verified with a multi-physics simulator. All these elements are working iteratively together to prepare a valid execution plan that is finally uploaded to the spacecraft for execution. Based on the monitoring and feedback information received from the spacecraft during the operations (e.g. detected failed module), the MCC can update the execution plan. The MCC finally includes visualisation front-end to support the design, verification and monitoring activities during sequence execution.

## 3.2 Formalism

The following section details the system requirements following the structure exemplified in this table:

Table 2: Example of requirement
<table><tr><td rowspan=1 colspan=1>YY_uniquelD</td><td rowspan=1 colspan=3>Title</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>Requirement Statement</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design (ROD) /Analysis / Inspection / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>PSA_FuncR_A000</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS, DLR, GMV, TAS-F, TAS-UK, SITAEL, MAGSOAR, USTRAT,ELLIDISS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Additional comment and explanations</td></tr></table>

The top row of the table includes:

● Unique ID: identificator with the structure YY\_uniqueID

○ YY: type of the requirement - Functional requirements (FuncR), Performance requirements (PerfR), Interface requirements (IntR), …

○ uniqueID: unique reference with 4 characters:

■ The first character is a letter identifying the subsystem the requirement belongs to

■ The next number identifies the type of requirement inside the subsystem

The next two numbers identify a number assigned to each requirement in that category

● Title: highlighting the topic of the requirement

● LEVEL: indicates the level of importance of the requirement (mandatory / desirable / optional) The rest of the table includes the following fields:

● STATEMENT: clear and concise description of the requirement

● VERIFICATION METHOD: indicates how the requirement is going to be verified (simulation, internal testing, lunar analog testing) with a short description of the validation process (1 to 3 lines)

COVERS: gives indication about the origin/scope of the requirements (specific user requirement or user case, partner expertise, project constraint, etc.)

● RESPONSIBLE: indicates which partner is responsible for the verification and follow up of the requirement

● COMMENT: provides rationale or additional comments about the requirement

## 3.3 System Requirements [Axxx]

This section and following ones list the requirements for the physical demonstrator system and subsystems developed in MOSAR.

3.3.1 A100: Functional requirements [FuncR]
<table><tr><td rowspan=1 colspan=1>FuncR_A101</td><td rowspan=1 colspan=3>Demonstrator purpose</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The MOSAR demonstrator shall illustrate the repair and update of modular spacecraftby manipulation and repositioning of SM with the WM.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S101, FuncR_S102</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_A102</td><td rowspan=1 colspan=3>Demonstrator components</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The MOSAR demonstrator shall include:A set of spacecraft modules (ASM/APM) to illustrate the scenarios andfunctionalities of modular spacecraftA robotic walking manipulator for the manipulation of the SMA servicer satellite and client modular spacecraft mockup to support thedemonstration scenariosA monitoring and control center that includes a design and simulation tool tocreate and simulate the execution plan and a monitoring interface</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Guidelines AD1Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_A103</td><td rowspan=1 colspan=3>Plan execution</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SVC OBC shall execute autonomously the assembly/ reconfiguration plan preparedby the design and simulation tool</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S107MOSAR Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>None</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>FuncR_A104</td><td rowspan=1 colspan=3>SVC high level control</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SVC OBC shall perform the high-level control of the WM, SM and SI for theexecution of the assembly/ reconfiguration plan</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S107MOSAR Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV / DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>None</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_A105</td><td rowspan=1 colspan=3>Components low level control</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>Low level control of the WM, SM and SI shall be performed locally by each component</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S108MOSAR Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPSS, DLR, SITAEL, TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>This allow to relax constraints on the data bus requirements (e.g. high rate roboticcontrol), the SVC OBC having to send only high level commands to the components</td></tr></table>

<table><tr><td>FuncR_A106</td><td colspan="3">WM modules operations</td><td>Mandatory</td></tr><tr><td>STATEMENT</td><td colspan="3">The WM shall be able to add and replace SM (ASM/APM) by using SI.</td><td></td></tr><tr><td>VERIFICATION</td><td>Testing</td><td>COVERS</td><td colspan="2">FuncR_S103 Operational Concept RD3</td></tr><tr><td>RESPONSIBLE</td><td colspan="3">SPACEAPPS / DLR</td><td></td></tr><tr><td>COMMENT</td><td colspan="3">None</td><td></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_A107</td><td rowspan=1 colspan=3>WM relocation</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall be able to reposition itself by using the Sl of the functional modules or theplatform</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S104Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS / DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>None</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>FuncR_A108</td><td rowspan=1 colspan=3>Monitoring</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SVC OBC shall be able to monitor the parameters of the SM, WM and SI</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S109</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV, SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>None</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_A109</td><td rowspan=1 colspan=3>Spacecraft reconfiguration</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The system shall be able to re-configure the CLT (e.g. SM exchange) in case of a defect(e.g. malfunction of a SM)</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S101</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV, DLR, SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_A110</td><td rowspan=1 colspan=3>System redundancy</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The system shall be able to re-route and reallocate resources (e.g. power, data,computational power, etc.) in case of a defect (e.g. interconnector of an APM)</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S110, FuncR_S120,FuncR S122, SafR S813,SafR_S814</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV, DLR, SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>This should support connection failure or a power interruption of defect modules /interconnectors. Computational power can only be done in the simulator.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_A111</td><td rowspan=1 colspan=3>Modules Plug &amp; Play detection</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SVC OBC shall be able to detect and use additional functional modules (plug &amp;play principle)</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S102</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV, ELLI, UBREST, TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>FuncR_A112</td><td rowspan=1 colspan=3>Fault detection</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SVC OBC shall be able to react to a faulty behavior detected by the SM, WM or SI</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>SafR_S808</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The reaction could include local management on the spacecraft (e.g. SM isolation) orfeedback to the MCC</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_A113</td><td rowspan=1 colspan=3>3D reconstruction through WM</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>A 3D reconstruction of the satellite could be produced from the observation by a cameramounted on the WM, with a maximum surface average error of 1cm</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Re-use of OG3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>USTRATH</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Supported after re-configuration process. The WM is used to obtain different view pointsThe 3D reconstruction should allow a human operator to assess the correctness of there-configuration, and 1cm maximum surface error should be enough to meet the target</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_A114</td><td rowspan=1 colspan=3>3D reconstruction through SM</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>A 3D reconstruction of the satellite could be produced from the observation by a cameramounted in a SM, with a maximum surface average error of 1cm</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Re-use of OG3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>USTRATH</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Supported during re-configuration process, in real time (30 frames/sec)The 3D reconstruction should allow a human operator to assess the correctness of there-configuration, and 1cm maximum surface error should be enough to meet the target.</td></tr></table>

<table><tr><td colspan="1" rowspan="1">FuncR_A115</td><td colspan="3" rowspan="1">Camera Localization</td></tr><tr><td colspan="1" rowspan="1">STATEMENT</td><td colspan="3" rowspan="1">The 3D pose estimation of the camera mounted on the WM could be computed basedon the image stream, with a mean error not larger than 1 cm translation and 5° rotation,with a minimum of 30 frame/sec</td></tr><tr><td colspan="1" rowspan="1">VERIFICATION</td><td colspan="1" rowspan="1">Testing</td><td colspan="1" rowspan="1">COVERS</td><td colspan="1" rowspan="1">Re-use of OG3</td></tr><tr><td colspan="1" rowspan="1">RESPONSIBLE</td><td colspan="3" rowspan="1">USTRATH</td></tr><tr><td colspan="1" rowspan="1">COMMENT</td><td colspan="3" rowspan="1">The accuracy of the estimated pose should allow correct positioning and connection ofthe hardware interfaces. It should also allow 3D reconstruction with errors defined in</td></tr><tr><td></td><td colspan="3">FuncR_A113 and FuncR_A114. 1cm translation and 5° rotation errors is a reasonable previously achieved target that are compatible with the initiation of the connection process of the interconnectors through the use of the form-fit guidance. Furthermore, localization has to happen in real time, and 30 milliseconds / frame is an acceptable value achieved by recent 3d localization and mapping algorithms as described in RD2.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_A116</td><td rowspan=1 colspan=3>SM Localization</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The 3D pose estimation of the SM could be computed based on the image streamobtained by the camera mounted on the WM, with a mean error not larger than 1 cmtranslation and 5° rotation, with a minimum of 30 frame/sec (first estimation of a newmodule 10 sec after appearance)</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Re-use of OG3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>USTRATH</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The accuracy of the estimated pose should allow correct positioning and connection ofthe hardware interfaces. It should also allow 3D reconstruction with errors defined inFuncR_A113 and FuncR_A114. 1cm translation and 5° rotation errors is a reasonablepreviously achieved target that are compatible with the initiation of the connectionprocess of the interconnectors through the use of the form-fit guidance. Furthermore,localization has to happen in real time, and 30 milliseconds / frame is an acceptablevalue achieved by recent 3d localization and mapping algorithms as described in RD2.Initial detection of a module does not require real-time capabilities, but needs to beachieved in useful operating time, 10 seconds is an acceptable operation delay.</td></tr></table>

## 3.3.2 A200: Performance requirements [PerfR]

<table><tr><td rowspan=1 colspan=1>PerfR_A201</td><td rowspan=1 colspan=3>Sub-systems TM/TC data rate</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>TM/TC control of the WM and SM, including their SI, by the SVC OBC shall require anetwork supporting a data rate of 1Mbps or greater</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>TAS-UK, SPACEAPPS, DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The TM/TC control of the platform should not rely on high data rate links with lowlatency.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>PerfR_A202</td><td rowspan=1 colspan=3>Sub-systems services data rate</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>SVC OBC shall require a network supporting a data rate of 50Mbps or greater for SMservice data.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>TAS-UK, SPACEAPPS, SITAEL</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td>COMMENT</td><td>For a camera APM, at 50 Mbps, a 4Mpixel image will take several seconds to transfer across the data network.</td></tr></table>

## MOSAR - System Requirements Document

3.3.3 A300: Interface requirements [IntR]
<table><tr><td rowspan=1 colspan=1>IntR_A301</td><td rowspan=1 colspan=3>SVC to CLT mechanical interface</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SVC shall provide a mechanical docking connection to the CLT</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OpR_S603Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL, TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The docking procedure is not part of the In MOSAR demonstration scenarios. Bothspacecraft will be rigidly connected all along the demonstrations with a representativegap.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_A302</td><td rowspan=1 colspan=3>SVC to CLT data interface</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SVC shall provide a data interface to the CLT to connect both internal networks</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OpR_S604Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL, TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The data interface allows the SVC to take the control of all the components for theexecution of the re-configuration plan</td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_A303</td><td rowspan=1 colspan=3>SVC to CLT power interface</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SVC shall provide a power interface to the CLT to be able to power CLTcomponents</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL, TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Not required as, in the demonstration, the CLT could have his own power sub-system</td></tr></table>

<table><tr><td colspan="1" rowspan="1">IntR_A304</td><td colspan="3" rowspan="1">MCC to SVC data link</td></tr><tr><td colspan="1" rowspan="1">STATEMENT</td><td colspan="3" rowspan="1">The MCC shall provide a data link for upload of the execution plan and TM/TC serviceswith the SVC</td></tr><tr><td colspan="1" rowspan="1">VERIFICATION</td><td colspan="1" rowspan="1">Review of Design</td><td colspan="1" rowspan="1">COVERS</td><td colspan="1" rowspan="1">OpR_S605Operational Concept</td></tr><tr><td colspan="1" rowspan="1">RESPONSIBLE</td><td colspan="3" rowspan="1">GMV, DLR</td></tr><tr><td colspan="1" rowspan="1">COMMENT</td><td colspan="3" rowspan="1">Represent the satellite link communication, could implement space standard</td></tr><tr><td></td><td colspan="3">communication protocols, e.g. the packet utilization standard (PUS) to give some level of representativeness to the demonstrator.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_A305</td><td rowspan=1 colspan=3>MCC to SVC debugging link</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The MCC shall provide a data link for monitoring and debugging purpose during theintegration and testing of the demonstrator</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Partner expertise</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_A306</td><td rowspan=1 colspan=3>SVC and CTL SI</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SVC and CTL shall provide SI to enable connection with the SM and the WM</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S110, FuncR_S118</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL, SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

3.3.4 A400: Design requirements [DesR]
<table><tr><td rowspan=1 colspan=1>DesR_A401</td><td rowspan=1 colspan=3>OG1 Reuse</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The platform shall implement ESROCOS from OG1 for the control of the system</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Guidelines AD1 OG9-R10</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>A number of adaptations and extensions are anticipate (see RD1)</td></tr></table>

<table><tr><td colspan="1" rowspan="1">DesR_A402</td><td colspan="3" rowspan="1">OG2 Reuse</td></tr><tr><td colspan="1" rowspan="1">STATEMENT</td><td colspan="3" rowspan="1">The platform shall implement autonomy functions using OG2 (ERGO)</td></tr><tr><td colspan="1" rowspan="1">VERIFICATION</td><td colspan="1" rowspan="1">Review of Design</td><td colspan="1" rowspan="1">COVERS</td><td colspan="1" rowspan="1">Guidelines AD1 OG9-R10</td></tr><tr><td colspan="1" rowspan="1">RESPONSIBLE</td><td colspan="3" rowspan="1">GMV</td></tr><tr><td colspan="1" rowspan="1">COMMENT</td><td colspan="3" rowspan="1">A number of adaptations and extensions are anticipate (see RD1)</td></tr><tr><td colspan="1" rowspan="1">DesR_A403</td><td colspan="3" rowspan="1">OG3 Reuse</td></tr><tr><td colspan="1" rowspan="1">STATEMENT</td><td colspan="3" rowspan="1">The platform shall implement sensor data fusion techniques from OG3 (Infuse)</td></tr><tr><td colspan="1" rowspan="1">VERIFICATION</td><td colspan="1" rowspan="1">Review of Design</td><td colspan="1" rowspan="1">COVERS</td><td colspan="1" rowspan="1">Guidelines AD1 OG9-R10</td></tr><tr><td colspan="1" rowspan="1">RESPONSIBLE</td><td colspan="3" rowspan="1">USTRATH</td></tr><tr><td colspan="1" rowspan="1">COMMENT</td><td colspan="3" rowspan="1">The WM operations would rely only on known geometry information, without the need ofdata fusion techniques. To be discussed and decided at SRR if data fusion techniquesare illustrated in the scenario (e.g. SVC visual validation)</td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_A404</td><td rowspan=1 colspan=3>OG4 Reuse</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The satellite shall be equipped with its own integrated R-ICU derived from the OG4I3DS architecture and illustrate operations of functional modules equipped with selectedsensors suite from I3DS</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Guidelines AD1 OG9-R10</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>TAS-UK, TAS-F</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>A number of adaptations and extensions are anticipate (see RD1)</td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_A405</td><td rowspan=1 colspan=3>OG5 Reuse</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The required H/W units in OG9 (platform, ASMs/APMs, robot) shall be equipped withstandard interfaces from OG5.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Guidelines AD1 OG9-R10</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>A number of adaptations and extensions are anticipate (see RD1)</td></tr></table>

<table><tr><td colspan="1" rowspan="1">DesR_A406</td><td colspan="3" rowspan="1">SVC and CLT OBC</td></tr><tr><td colspan="1" rowspan="1">STATEMENT</td><td colspan="3" rowspan="1">The SVC and CLT spacecraft shall have on OBC for the management of the differentcomponents associated with the spacecraft and the communications</td></tr><tr><td colspan="1" rowspan="1">VERIFICATION</td><td colspan="1" rowspan="1">Review of Design</td><td colspan="1" rowspan="1">COVERS</td><td colspan="1" rowspan="1">FuncR_S114</td></tr><tr><td colspan="1" rowspan="1">RESPONSIBLE</td><td colspan="3" rowspan="1">SITAEL</td></tr><tr><td colspan="1" rowspan="1">COMMENT</td><td colspan="3" rowspan="1">In the MOSAR demonstration, the SVC OBC should take the lead on all thecomponents of the system.</td></tr><tr><td colspan="1" rowspan="1">DesR_A407</td><td colspan="3" rowspan="1">Data Network</td></tr><tr><td colspan="1" rowspan="1">STATEMENT</td><td colspan="3" rowspan="1">The system shall implement a data technology network that supports data bus re-configuration and routing</td></tr><tr><td colspan="1" rowspan="1">VERIFICATION</td><td colspan="1" rowspan="1">Review of Design / Testing</td><td colspan="1" rowspan="1">COVERS</td><td colspan="1" rowspan="1">FuncR S110, FuncR S119</td></tr><tr><td colspan="1" rowspan="1">RESPONSIBLE</td><td colspan="3" rowspan="1">TAS-UK</td></tr><tr><td colspan="1" rowspan="1">COMMENT</td><td colspan="3" rowspan="1">In the MOSAR demonstration, the SVC OBC should take the lead on all thecomponents of the system.The current selected technology is SpaceWire based on the developments and outputsof OG4</td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_A408</td><td rowspan=1 colspan=3>Relevance to flight hardware</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The demonstrator design should not be de-rated for demonstration use and berepresentative of an actual space system in terms of capabilities (e.g. mass movementcapacity, speed of reconfiguration, processing capacity of on-board computing), whilestill retaining feasibility of operation in Earth&#x27;s gravity (so as to be functional)</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>PERASPERA final objectives</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>ALL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## 3.3.5 A500: Physical and resource requirements [PhyR]

N./A.

## 3.3.6 A600: Environmental and Operational requirements [OpR]

<table><tr><td rowspan=1 colspan=1>OpR_A601</td><td rowspan=1 colspan=3>Laboratory Environment</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The demonstrator shall be able to work under laboratory conditions in a temperaturerange between 10 and 30 deg</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Demonstration Constraint</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>ALL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>OpR_A602</td><td rowspan=1 colspan=3>Gravity conditions</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The demonstrator shall be able to work under 1g</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Demonstration Constraint</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>ALL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>OpR_A603</td><td rowspan=1 colspan=3>Demonstrator Power supply</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The demonstrator shall be able to be powered from standard power plugs</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Demonstration Constraint</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>ALL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## 3.3.7 A700: Safety requirements [SafR]

<table><tr><td rowspan=1 colspan=1>SafR_A701</td><td rowspan=1 colspan=3>Demonstrator Safety</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>Demonstrator shall be inherently safe during operation, considering the implementationin a laboratory environment with trained operators</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Safety rules</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>ALL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Safety should consider mechanical and electrical potential issue. Safety can beaddressed by system design (limited speeds, compliance) and/or throughimplementation of safety features (Emergency stops, interlocks or sensors barriers)</td></tr></table>

## 3.3.8 A800: Configuration and implementation requirements [ConfR]

<table><tr><td rowspan=1 colspan=1>ConfR_A801</td><td rowspan=1 colspan=3>SVC and TGT test bench</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>A test bench shall be designed and integrated to represent the SVC satellite to the CLTspacecraft, considering the gap existing between both the platform during dockingcondition</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design, Inspection</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OpR_S603Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>ConfR_A801</td><td rowspan=1 colspan=3>Test bench mechanical structure</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The structure of the test bench shall be stable and able to carry the own mass and theloads introduced by the SMs and WM</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design, Analysis</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Preliminary MOSAR demonstrator</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>ConfR_A802</td><td rowspan=1 colspan=3>Test bench SI interfaces</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SVC and CTL test benches shall provide the required number of SI to cover theMOSAR scenario demonstrations</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>IntR_A306</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL, SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr><tr><td rowspan=1 colspan=1>ConfR_A803</td><td rowspan=1 colspan=3>Test bench harnessing</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The test bench shall include the internal and external harnessing of the SVC and CTLspacecraft and the connected SI</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design, Inspection</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept RD3Preliminary MOSAR demonstrator</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL, SPACEAPPS, TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## 3.4 Walking Manipulator Requirements [Bxxx]

3.4.1 B100: Functional requirements [FuncR]
<table><tr><td rowspan=1 colspan=1>FuncR_B101</td><td rowspan=1 colspan=3>SM connection</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall be able to connect to the SI of the SM or the spacecraft mockupindependently through one of its own SI</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_A106, FuncR_A107</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS, DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_B102</td><td rowspan=1 colspan=3>SM manipulation</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall be able to move and assemble the functional modules in a 3-dimensionalway</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_A106</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS, DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_B103</td><td rowspan=1 colspan=3>Joint position control</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall provide local joint position control at minimum 500 Hz</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Operational ConceptPartner Expertise</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR, SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_B104</td><td rowspan=1 colspan=3>Cartesian position control</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall provide local Cartesian position control of the free end-effector atminimum 500 Hz</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Operational ConceptPartner Expertise</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR, SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>To support manipulation of the SM along pre-defined trajectories and initial SI alignment</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>FuncR_B104</td><td rowspan=1 colspan=3>Impedance control</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall provide impedance control at minimum 500 Hz</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Operational ConceptPartner Expertise</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR, SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>To support Sl alignment or connection process</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_B105</td><td rowspan=1 colspan=3>Fault detection</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall be able to detect malfunction of its operations</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_A112</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_B106</td><td rowspan=1 colspan=3>Power-on/off</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall be able to be powered on/off, keeping its current position</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>To reduce consumption when the WM is not in use. The power switch could bemanaged at the SI level</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_B107</td><td rowspan=1 colspan=3>WM start and initialization</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall be able to start and initialize automatically after power-on, reaching astate ready for communication and operations</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>FuncR_B106</td><td rowspan=1 colspan=3>WM perception</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM could have the ability to perceive the location of SMs in three dimensions to anerror of 1cm using attached stereo vision sensors.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR, USTRATH</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Not required with the current approach of WM SM approach and manipulation (basedon known geometry and SM localization). Would require additional sensors</td></tr></table>

3.4.2 B200: Performance requirements [PerfR]
<table><tr><td rowspan=1 colspan=1>PerfR_B201</td><td rowspan=1 colspan=3>WM payload capability</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall be able to manipulate a payload of 7kg all around his workspace</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Demonstration ScenarioOpR_A602</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The target is to not implement external gravity compensation on the SM, TBCdepending on the updated weight estimations during PDR</td></tr></table>

<table><tr><td rowspan=1 colspan=1>PerfR_B202</td><td rowspan=1 colspan=3>WM reachability</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM kinematic structure shall be compatible in size and joint configuration tosupport all MOSAR scenarios demonstrations</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Demonstration ScenarioDesR_S404</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Kinematic configuration and reachability analyzed during PDR phase</td></tr></table>

<table><tr><td rowspan=1 colspan=1>PerfR_B203</td><td rowspan=1 colspan=3>WM data interface rate for TM/TC</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The data interface of the WM shall support a data rate of 1Mbps or greater for TM/TCcontrol.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Operational ConceptPerfR A201</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS, DLR, TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The TM/TC control of the platform should not rely on high data rate links with lowlatency.</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>PerfR_B204</td><td rowspan=1 colspan=3>WM data interface rate for service data</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The data interface of the WM shall support a data rate of 50 Mbps or greater for servicedata.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Operational ConceptPerfR_A202</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS, DLR, TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>E.g. to support data transfer from a connected SMThe services provided by the Spacecraft Module share the same data interface asTM/TC and will have a higher bandwidth requirement. At 50 Mbps, a 4Mpixel image willtake several seconds to transfer across the data network.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>PerfR_B205</td><td rowspan=1 colspan=3>WM power interface rate</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The power interface of the WM shall support 0.5kW [TBC] of power transfer</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Operational ConceptPerfR_A202</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>For the operation of the WM and one connected SM (APM). Value TBC for PDR</td></tr></table>

3.4.3 B300: Interface requirements [IntR]
<table><tr><td rowspan=1 colspan=1>IntR_B301</td><td rowspan=1 colspan=3>WM TM/TC</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall transmit telemetry and receive high-level tele-command with the SVCOBC, independently through the data interface of one of the connected SI</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>IntR_B302</td><td rowspan=1 colspan=3>WM data transfer</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall be able to transmit TM/TC and data from the SVC OBC with the SMconnected at its SI</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational ConceptGuidelines AD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_B303</td><td rowspan=1 colspan=3>WM power</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall get power from the spacecraft/modules through the power interface of theconnected SI</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_B304</td><td rowspan=1 colspan=3>WM power transfer</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall be able to transmit power to the SM connected at its SI</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_B304</td><td rowspan=1 colspan=3>WM interface switch</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall be able to switch power and data interface between the two Sl extremities</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>IntR_B305</td><td rowspan=1 colspan=3>WM local CAN network</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall provide a local CAN network to interface and control the end-effectors SI</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>CAN network technology is currently selected based on OG5 outputs</td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_B306</td><td rowspan=1 colspan=3>WM local control network</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall be able to parse information from/to its data interface through the two SIextremities and translate it in its own local bus for Real-Timer monitor and control of itsjoins.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_B307</td><td rowspan=1 colspan=3>WM mechanical interface to SI</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall provide a mechanical interface connection at each extremity to attach aSI</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

3.4.4 B400: Design requirements [DesR]
<table><tr><td rowspan=1 colspan=1>DesR_B401</td><td rowspan=1 colspan=3>SI as WM end-effectors</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall be equipped with a Sl at each of its extremities</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>DesR_B402</td><td rowspan=1 colspan=3>Embedded controller</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall have an embedded local controller to convert high-level controlcommands from the SVC OBC to low-level control of the joints</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S108MOSAR Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_B403</td><td rowspan=1 colspan=3>Torque/force sensors</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The WM shall be equipped with Force/Torque sensors to support the implementation ofthe impedance control</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>End-tip of joint torque TBC</td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_B404</td><td rowspan=1 colspan=3>Compatibility to environmental tests conditions</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The design of the WM shall be such that it is able to withstand the test environmentalconditions</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Demonstration constraints</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_B405</td><td rowspan=1 colspan=3>Compatibility to space design</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The design of the WM shall be such that the later product is able to withstand the harshconditions in space</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Guidelines RD3 OG9-R09OpR_S606</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

3.4.5 B500: Physical and resource requirements [PhyR]
<table><tr><td rowspan=1 colspan=1>PhyR_B501</td><td rowspan=1 colspan=3>WM weight</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The weight of the WM shall minimized with a targeted weight of 14kg [TBC], includingthe SI.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>PhyR_S501</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Based on the assumption of a 1 to half payload capability of 7kg</td></tr></table>

3.4.6 B600: Environmental and Operational requirements [OpR] N./A.

3.4.7 B700: Safety requirements [SafR] N./A.

3.4.8 B800: Configuration and implementation requirements [ConfR] N./A.

## 3.5 Spacecraft Modules Requirements [Cxxx]

3.5.1 C100: Functional requirements [FuncR]
<table><tr><td rowspan=1 colspan=1>FuncR_C101</td><td rowspan=1 colspan=3>SM functions</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SMs shall provide all required support functions to any embarked unit andguarantee the required operative profile during the lifetime</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design, Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_C102</td><td rowspan=1 colspan=3>SM components</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>Each SM shall be able to host all the components needed to fulfill its functions</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Guidelines AD1 OG9-R11</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_C103</td><td rowspan=1 colspan=3>SM data routing configuration</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The baseline functionality of a Spacecraft Module shall include the ability to externallyconfigure the SM&#x27;s data routing function between the Standard Interfaces and servicesprovided by SM</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR S120MOSAR Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>FuncR_C104</td><td rowspan=1 colspan=3>SM data transmission</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The baseline functionality of a Spacecraft Module shall include the ability to provideexternal TM/TC control and service data of the Spacecraft Module via the SM datainterface once the routing function has been configured</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S119, FuncR_A108MOSAR Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_C103</td><td rowspan=1 colspan=3>SM rower routing configuration</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The baseline functionality of a Spacecraft Module shall include the ability to externallyconfigure the SM&#x27;s power routing function between the Standard Interfaces</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>This can be envisaged by an internal power distribution unit in the SM or at the SI level</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_C105</td><td rowspan=1 colspan=3>SM redundancy</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The assembled modules shall be able to switch to redundant data and power paths</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_A110</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>TAS-UK, SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_C106</td><td rowspan=1 colspan=3>SM power-on/off</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SM shall be able to be powered on/off or put in stand-by mode, keeping itscapability to transmit data and power to other SM</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>To reduce consumption when the SM is not in use.</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>FuncR_C107</td><td rowspan=1 colspan=3>SM start and initialization</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SM shall be able to start and initialize automatically after power-on, reaching a stateready for communication and operations</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL, TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_C108</td><td rowspan=1 colspan=3>Identification information</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SM shall be able to provide identification information including unique identifiernumber and list of capabilities</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_A111</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL, TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>To support automatic detection and plug and play operations</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_C109</td><td rowspan=1 colspan=3>Fault detection</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SM shall be able to detect malfunction of its operations</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_A112</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

3.5.2 C200: Performance requirements [PerfR]
<table><tr><td rowspan=1 colspan=1>PerfR_C201</td><td rowspan=1 colspan=3>SM data interface rate for TM/TC</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The data interface of the Spacecraft Module shall support a data rate of 1Mbps orgreater for TM/TC control.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Operational ConceptPerfA_A202</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS, DLR, TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The TM/TC control of the platform should not rely on high data rate links with lowlatency.</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>PerfR_C202</td><td rowspan=1 colspan=3>SM data interface rate for service data</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The data interface of the Spacecraft Module shall support a data rate of 50 Mbps orgreater for service data.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Operational ConceptPerfA_A203</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS, DLR, TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The services provided by the Spacecraft Module share the same data interface asTM/TC and will have a higher bandwidth requirement. At 50 Mbps, a 4Mpixel image willtake several seconds to transfer across the data network.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>PerfR_C203</td><td rowspan=1 colspan=3>SM power interface rate</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The power interface of the SM shall support [1-2kW] [TBC] of power transfer</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational ConceptRD3PerfR_A202</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL, SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The power APM should be able to deliver the required power for the operations of theother SM, WM and SI. Value TBC for PDR</td></tr></table>

## 3.5.3 C300: Interface requirements [IntR]

<table><tr><td rowspan=1 colspan=1>IntR_C301</td><td rowspan=1 colspan=3>SM power</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SM shall get power from the power interface of one of the connected SI</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_C302</td><td rowspan=1 colspan=3>SM R-ICU power Up</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The Spacecraft Module&#x27;s R-ICU shall be powered up whenever external power issupplied to any of its Standard Interfaces.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL, SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Enables plug and play of Spacecraft Modules.</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>IntR_C303</td><td rowspan=1 colspan=3>SM R-ICU to SI TM/TC</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The R-ICU shall provide TM/TC control of the Standard Interfaces using CANbus</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS, TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The R-ICU is the CAN bus master and the Standard Interfaces are all slaves to the R-ICU. CAN network technology is currently selected based on OG5 outputs</td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_C304</td><td rowspan=1 colspan=3>SM mechanical interface to SI</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SM shall provide a mechanical interface connection to attach a Si</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

3.5.4 C400: Design requirements [DesR]
<table><tr><td rowspan=1 colspan=1>DesR_C401</td><td rowspan=1 colspan=3>SM structure</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SM structure shall be composed by the following units:6 lateral panels12 beams4 cornersConnection items (to connect all the units of the SMs with the structuralunits of the SMs)</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Partner expertise</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>For improved cross-compatibility of launchers and internal systems, SMs should targetto the form factor for a cubic 27U CubeSat (RD1).</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>DesR_C402</td><td rowspan=1 colspan=3>Number of SI</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>All SM shall have a sufficient number of SI in order to manipulate them with the WM andto couple them with each other and to the SVC or CLT</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept RD3Guidelines AD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL, DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>A maximum number of 3 Sl are currently considered as optimization betweendemonstration application and demonstration constraints (weight, costs)</td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_C403</td><td rowspan=1 colspan=3>SM mechanical loading</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The structure of the modules shall be able to carry its own mass under the gravity forceand the loads introduced by the “walking” robot-system during the manipulation of theSMs.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Analysis, Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept RD3Guidelines AD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_C404</td><td rowspan=1 colspan=3>SM mechanical loading data</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The forces applied by the WM and the motion dynamics shall be provided for the designof the SMs in the worst case.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Analysis</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Partner Expertise</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_C405</td><td rowspan=1 colspan=3>SM physical layout</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SMs physical layout shall allow the accommodation of all the equipment, byguaranteeing the proper mechanically assembly, the thermo-mechanical behavior, theŠM mechanical/electrical integration and testing, as required by the test requirements</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Partner expertise</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>DesR_C406</td><td rowspan=1 colspan=3>SM accommodation</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The accommodation of the units shall take into account the following criteria:Need of assembly and disassemblyEasy access to the electrical connectors, fixation points, grounding studsAlignment requirementsMass distributionEnvelopeHarness routingFOV constraints (in the case of the integration of optical sensors)</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design, Inspection,Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Partner expertise</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_C407</td><td rowspan=1 colspan=3>SM accommodation flexibility</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SMs structure shall be flexible in order to allow the accommodation of different kindof internal equipment</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Inspection</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Mission analysis RD2Guidelines AD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_C408</td><td rowspan=1 colspan=3>SM face assignation</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>Only the assigned faces of the SM shall host the standard interfaces.While, only one customized face for each SM shall host all the other units needed tofulfill the SM functions.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Partner Expertise</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>DesR_C409</td><td rowspan=1 colspan=3>Thermal conditions</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SMs shall be design in order to guarantee the required thermal conditions to all theunits mounted inside the SMs</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design, Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Partner Expertise</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_C405</td><td rowspan=1 colspan=3>Compatibility to environmental tests conditions</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The design of the SM shall be such that it is able to withstand the test environmentalconditions</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Demonstration constraints</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_C406</td><td rowspan=1 colspan=3>Compatibility to space design</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The design of the SM shall be such that the later product is able to withstand the harshconditions in space</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Guidelines RD3 OG9-R09OpR_S606</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

3.5.5 C500: Physical and resource requirements [PhyR]
<table><tr><td rowspan=1 colspan=1>PhyR_C501</td><td rowspan=1 colspan=3>SM Weight</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The weight of the SM shall be minimized with a target mass of 7kg [TBC]</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>PhyR_S501</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>For improved cross-compatibility of launchers and internal systems, SMs should targetto the form factor for a cubic 27U CubeSat (RD1).</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>DesR_C502</td><td rowspan=1 colspan=3>SM size</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SM shall be cubical in shape in size 300 to 400 mm (TBD) per side</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Mission analysis RD2</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>For improved cross-compatibility of launchers and internal systems, SMs should targetto the form factor for a cubic 27U CubeSat (RD1).</td></tr></table>

## 3.5.6 C600: Environmental and Operational requirements [OpR]

3.5.7 C700: Safety requirements [SafR]
<table><tr><td rowspan=1 colspan=1>SafR_C701</td><td rowspan=1 colspan=3>SM hand manipulation</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SM shall be able to be safely manipulated by hand</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Inspection</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Safety rules</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

3.5.8 C800: Configuration and implementation requirements [ConfR]
<table><tr><td>ConfR_C801</td><td colspan="2">Demonstrator SM Configurations</td><td colspan="2"></td><td>Mandatory</td></tr><tr><td>STATEMENT</td><td colspan="5">A set of 7 SMs shall be developed, with the following functions: 4 ASMs: O Data Management Subsystem module (DMS): this ASM hosts the main Onboard Computer of the target spacecraft. O Power Subsystem (PWS): is managing the electrical power on the TGT spacecraft. O Battery ORU module (BAT): is an SM that comprises a set of Lithium- ion batteries and the electronic to manage them. O Thermal Subsystem module (THS): is responsible for the thermal management of the TGT SMs 2 APMs Optical Sensor Payload module (OSP): is an SM that exposes an optical lens on one of its faces. 1 back-up SM</td></tr><tr><td>VERIFICATION</td><td colspan="2">Review of Design</td><td>COVERS</td><td>FuncR_S112, FuncR_S114, FuncR_S115 Scenarios Description</td><td></td></tr><tr><td>RESPONSIBLE</td><td colspan="5">SITAEL</td></tr><tr><td>COMMENT</td><td colspan="5">Selection of ASM and APM are illustrative to the possible missions scenario, final selection and specifications of each developed module at PDR</td></tr></table>

## 3.6 Standard Interfaces Requirements [Dxxx]

3.6.1 D100: Functional requirements [FuncR]
<table><tr><td rowspan=1 colspan=1>FuncR_D101</td><td rowspan=1 colspan=3>Mechanical, Data and Electrical Interface</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The standard interface shall providea mechanical interface to mechanically couple two system componentsan electrical interface to transfer electrical energy (power) between two systemcomponentsa data interface to allow exchange of data between two system components</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>MOSAR system components include Spacecraft Modules, Spacecraft Bus and WalkingManipulator</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_D102</td><td rowspan=1 colspan=3>Thermal Interface</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The standard interface shall provide a thermal interface to allow active transfer ofthermal flow between two Spacecraft Modules</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>In MOSAR, active thermal transfer is only considered between SM (not with theSpacecraft Bus or Walking Manipulator)</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_D103</td><td rowspan=1 colspan=3>Passive Coupling</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The standard interface shall allow the mechanical, power, data and thermal couplingwith another interface that cannot provide actuation</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Passive configurations of the Sl is currently envisaged in the scenarios for costsreductions (could also have an interest for future exploitation)</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>FuncR_D104</td><td rowspan=1 colspan=3>Passive Decoupling</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The standard interface shall allow the mechanical, power, data and thermal de-couplingwith another interface that cannot provide actuation</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_D105</td><td rowspan=1 colspan=3>Electrical Interface Protection</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The electrical interface shall have an overcurrent and overvoltage protection</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG5 RequirementInternal Expertise</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_D106</td><td rowspan=1 colspan=3>Electrical Interface Switch</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The electrical interface shall incorporate a bidirectional power switch to control currentflow at the interface.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S122</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Required to support (re)-routing of electrical power. Could also be managed by a centralpower distribution unit in the SM</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_D107</td><td rowspan=1 colspan=3>Electrical Interface Telemetry</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The electrical interface shall provide voltage and current telemetry at the power bussystem level, in both power transfer direction</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S122</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Required to monitor (re)-routing of electrical power.</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>FuncR_D108</td><td rowspan=1 colspan=3>Data Interface Support</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The data interface shall support at least one technology with capabilities of dynamicdata bus re-configuration and routing</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>DesR_A407</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS / TAS-UK</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Current selected technology in MOSAR is SpaceWire, based on OG4 outputs</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_D109</td><td rowspan=1 colspan=3>SI Telemetry</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SI shall measure and store the following local SI parameters:Temperature (Power electronics if local, structure)Alignment / proximity statusLocking statusSI orientation (in relation with design symmetry)Data/Power interface statusThermal interface statusMotor position (incremental or absolute) / Mechanism position (absolute)Motor currentController supply voltage</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Needed to monitor the function of the SI and support autonomous operation in MOSAR</td></tr></table>

3.6.2 D200: Performance requirements [PerfR]
<table><tr><td rowspan=1 colspan=1>PerfR_D201</td><td rowspan=1 colspan=3>Mechanical Loads</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The mechanical interface shall withstand, in connected mode, all mechanical loadsinduced by the demonstration operations:Axial Force: 250 / 160 NRadial Force: 250 / 160 NBending Moment: 204 / 84 NmTorsion: TBD NmAs function of the gravity compensation of the SM (TBC).</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Analysis / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1OpR_A602</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Best current estimationsRequired load transfer will depend on the configuration of the demonstrator setup andthe possible application of gravity mitigation technics. Due to the complexity of theoperations and motions, we currently target to not implement gravity compensation (leftnumber). We could however still envisage compensation of the SM (right number)</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>PerfR_D202</td><td rowspan=1 colspan=3>Positioning Tolerance</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The mechanical interface shall maximize positioning tolerance for guidance and mating</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Analysis / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>PerfR_D203</td><td rowspan=1 colspan=3>Power Transfer Rating</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The electrical interface shall be capable of supporting [1-2kW] (TBC) of power transfer,as required by the MOSAR demonstrationThe power interface of the SM shall support [1-2kW] [TBC] of power transfer</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Analysis / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>PerfR_C203</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Value TBC for PDR</td></tr></table>

<table><tr><td rowspan=1 colspan=1>PerfR_D204</td><td rowspan=1 colspan=3>Data Interface Rating</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The data interface shall allow a data rate of minimum 50Mbit/s</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Analysis / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>PerfR_A202</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>To support the recording and processing of large amounts of data between modulesand with the spacecraft, value TBC during PDR phase</td></tr></table>

<table><tr><td rowspan=1 colspan=1>PerfR_D205</td><td rowspan=1 colspan=3>Thermal Interface Rating</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The thermal interface shall allow a thermal flow rating of: TBD W</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Analysis / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>MAGSOAR / SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## MOSAR - System Requirements Document

3.6.3 D300: Interface requirements [IntR]
<table><tr><td rowspan=1 colspan=1>IntR_D301</td><td rowspan=1 colspan=3>Mechanical Interface to Components</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The standard interface shall provide a mechanical connection to the modules,spacecraft bus or robotic base/end-effector manipulator, compatible with the mechanicalloads transferred through the interface.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design / Analysis</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1IntR B307, IntR C304</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS, SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_D302</td><td rowspan=1 colspan=3>Harnessing to Components</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The standard interface shall provide internal harnessing to connect power, data andcontrol buses from the module, spacecraft or robotic base/end-effector manipulator</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS, SITAEL</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_D303</td><td rowspan=1 colspan=3>Interface to Module Thermal System</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The thermal interface shall enable thermal connection to the thermal module sub-system</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS, SITAEL, MAGSOAR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_D304</td><td rowspan=1 colspan=3>Power Distribution Unit</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SI shall be interfaced with a Power Distribution Unit (PDU) to provide low-levelvoltage power rails to supply the internal components of the SI (controller, sensors andmotor drives)</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Partner Expertise</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The PDU could be local to the SI or shared at module level</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>IntR_D305</td><td rowspan=1 colspan=3>Standard Interface TM/TC</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SI shall be able to send/receive local TM/TC to/from the module or spacecraft OBCTM: See FuncR_D109 listTC:Coupling / de-coupling (TBC for intermediate states)Electrical power transfer on/offLow-level control (TBC)</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_A104</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Based on OG5 developments, CAN is the current selected technology for SI TM/TC</td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_D306</td><td rowspan=1 colspan=3>Redundant Data/Power/Control Interface</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SI shall feature redundant data, power and control interface</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>SafR_S702</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>In case of failure, the Sl shall be able to switch to a redundant bus</td></tr></table>

## 3.6.4 D400: Design requirements [DesR]

<table><tr><td rowspan=1 colspan=1>DesR_D401</td><td rowspan=1 colspan=3>Androgynous Design</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The standard interface shall have an androgynous design, including mechanical, data,power and thermal interface</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_D402</td><td rowspan=1 colspan=3>Design Symmetry</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The standard interface shall present a 90deg. rotational symmetry, includingmechanical, data, power and thermal interface</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1ConfR_S902</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The standard interface shall allow module connections without restriction on relativemodule orientation</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>DesR_D403</td><td rowspan=1 colspan=3>Diagonal Engagement</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The standard interface shall allow diagonal engagement up to 55 deg</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>To enable multiple simultaneous approach and connection (e.g. corner example)</td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_D404</td><td rowspan=1 colspan=3>Form-Fit Guidance</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The standard interface shall provide guidance form-fit features</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>To support the alignment process between two interfaces, specifically when multipleconnections are considered, without requiring external guidance system</td></tr></table>

<table><tr><td rowspan=1 colspan=1>DesR_D405</td><td rowspan=1 colspan=3>SI Costs</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The design of the SI shall take into account optimization of the manufacturing andintegration costs</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Analysis</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>DesR_S403</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Cost should be a design driver considering the large quantity of interfaces in theproposed operational concept.</td></tr></table>

3.6.5 D500: Physical requirements [PhyR]
<table><tr><td rowspan=1 colspan=1>PhyR_D501</td><td rowspan=1 colspan=3>Standard Interface Mass</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The standard interface shall be optimized regarding the mass</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>PhyR_S501, PhyR_B501,PhyR_C501</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>PhyR_D502</td><td rowspan=1 colspan=3>Standard Interface Volume</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The standard interface shall be optimized regarding size and volume</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>PhyR_S502</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>To reduce constraints on the module design and integration</td></tr></table>

3.6.6 D600: Environmental and Operational requirements [OpR]
<table><tr><td rowspan=1 colspan=1>PhyR_D601</td><td rowspan=1 colspan=3>Standard Interface ShutDown</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The standard interface (or a part of it) shall be able to be switched off/on (behave as apassive plug), while ensuring data and power transfer.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>In regards to the total mission time, the operation time of the standard interface is verysmall. For energy optimization, it could be interesting to be able to switch off thecomponent (and be able to revive it later).</td></tr></table>

<table><tr><td>PhyR_D602</td><td colspan="3">Standard Interface Power Consumption</td><td>Mandatory</td></tr><tr><td>STATEMENT</td><td colspan="3">The power consumption of the standard interface shall be minimized</td><td></td></tr><tr><td>VERIFICATION</td><td>Testing</td><td>COVERS</td><td colspan="2">MOSAR Operational Concept OG5 Expertise</td></tr><tr><td>RESPONSIBLE</td><td colspan="3">SPACEAPPS</td><td></td></tr><tr><td>COMMENT</td><td colspan="3">Values TBC during PDR phase</td><td></td></tr></table>

<table><tr><td rowspan=1 colspan=1>PhyR_D603</td><td rowspan=1 colspan=3>Coupling Time</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The coupling time between two standard interfaces shall be minimized</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Operational Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>MOSAR demonstration will require a lot of successive mating/demating operations</td></tr></table>

## MOSAR - System Requirements Document

3.6.7 D700: Safety requirements [SafR]
<table><tr><td rowspan=1 colspan=1>SafR_D801</td><td rowspan=1 colspan=3>SI Safe Manipulation</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SI shall be safe to be manipulated during integration within SM, WM or SpacecraftBuses. If there exist potential risks, they shall be well documented</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Inspection</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Safety Rules</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## 3.6.8 D800: Configuration and implementation requirements [ConfR]

<table><tr><td rowspan=1 colspan=1>PhyR_D901</td><td rowspan=1 colspan=3>SI Design Configurations</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The standard interface shall be declined in different configurations that are:ActivePassive (not active behavior but can be couple and transmit data and power)Mechanical (not active and can only be coupled)Thermal (including thermal interface connectors, either active or passive)</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OGs costs and physicalcharacteristics constraints</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>This is mainly to support costs and volume/weight reduction in the grounddemonstrators. This could also be applicable in future mission depending on specificmission characteristics.</td></tr></table>

## 3.7 Planner and Simulator Requirements [Exxx]

3.7.1 E100: Functional requirements [FuncR]
<table><tr><td rowspan=1 colspan=1>FuncR_E101</td><td rowspan=1 colspan=3>Design and Simulation Tool Purpose</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The design and simulation software shall be able to simulate the system with all relatedrobotic elements and tasks (e.g. reconfiguration) as well as create a robotic compatibleservicing plan for the satellite platform</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S105, FuncR_S106</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR/GMV</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_E102</td><td rowspan=1 colspan=3>Design Software</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The software shall support engineers developing new components and satellites andshall give system integrators the chance to test the entire satellite including all relevantaspects of on-orbit assembly and servicing operation.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S105</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_E103</td><td rowspan=1 colspan=3>System Simulation</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The software shall allow users to simulation and test high-modular buildingblock space system architectures with regard to the requirements andconstraints of robotics, structure and the entire system</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>FuncR_S106</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>FuncR_E104</td><td rowspan=1 colspan=3>Task Planning and Simulation</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The software shall be used to plan and to test the servicing task of the robotsystem</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Guidelines AD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV (Planner) and DLR (Test)</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_E105</td><td rowspan=1 colspan=3>Simulation Topics</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The software shall allow to test and simulate the demonstration scenario regardingmechanical and thermal loads as well as distribution of resources.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Guidelines AD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_E106</td><td rowspan=1 colspan=3>Simulation of Reconfiguration</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The software shall allow the addition of functional modules to the spacecraft, performreconfiguration process, and simulate the servicing task considering dedicated roboticspecifications.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Guidelines AD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_E108</td><td rowspan=1 colspan=3>Environmental Conditions Simulation</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The simulation software shall be able to simulate the environmental conditions in LEO</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Inspection</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Mission Analysis RD2</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The effects of orbital disturbances and their respective relevance shall be verified basedon dedicated simulation output signals.</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>FuncR_E109</td><td rowspan=1 colspan=3>Manipulator Dynamics Simulation</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The simulation software shall be able to represent manipulator dynamics like motordynamics and joint flexibilities, if relevant in the demonstrator scenario.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Inspection</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

3.7.2 D200: Performance requirements [PerfR]
<table><tr><td rowspan=1 colspan=1>PerfR_E201</td><td rowspan=1 colspan=3>Simulation Real-Time Performance</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The simulation software shall be able to compute the reconfiguration scenarios in realtime as far as possible.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The real-time performance is verified during reference simulation runs (TBD).</td></tr></table>

<table><tr><td rowspan=1 colspan=1>PerfR_E202</td><td rowspan=1 colspan=3>Number of SM in Simulation</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The simulation software shall be able to process as many replaceable modules modelsas required according to the demonstration scenarios.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The ability to handle a sufficient number of modules is verified during referencesimulation runs (TBD).</td></tr></table>

3.7.3 D300: Interface requirements [IntR]
<table><tr><td rowspan=1 colspan=1>IntR_E301</td><td rowspan=1 colspan=3>Simulator Input Interfaces</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The simulation software of the FES shall be able to receive joint control inputs fromexternal joint controllers and planners..</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>IntR_E302</td><td rowspan=1 colspan=3>Simulator Output Interfaces</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The simulation software of the FES shall be able to feed back sensor information fromsensor models and simulation states to external controllers or a control console</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_E303</td><td rowspan=1 colspan=3>Simulator Communication Interface</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The simulation software shall be able to communicate with external entities via TCP/IPor UDP</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>IntR_E304</td><td rowspan=1 colspan=3>Generation of plan for onboard execution</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The ground instance of the ERGO Agent used to generate and validate thereconfiguration plan shall generate a static plan that can be transferred to and executedby the onboard ERGO Agent.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept RD3</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## 3.7.4 D400: Design requirements [DesR] N./A.

## MOSAR - System Requirements Document

3.7.5 D500: Physical and resource requirements [PhyR]
<table><tr><td rowspan=1 colspan=1>PhyR_E501</td><td rowspan=1 colspan=3>Simulator Computing Platform</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The FES shall run on an individual single-purpose PC</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Inspection / Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

3.7.6 D600: Environmental and Operational requirements [OpR] N./A.

3.7.7 D700: Safety requirements [SafR]

N./A.

3.7.8 D800: Configuration and implementation requirements [ConfR]
<table><tr><td rowspan=1 colspan=1>ConfR_E901</td><td rowspan=1 colspan=3>Scenario Simulation Models</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>For each scenario to be demonstrated, an individual simulation model shall be provided</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Inspection</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Partner Expertise</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>In order to minimize re-configuration activities</td></tr></table>

## 3.8 Software Requirements [Fxxx]

This section lists the requirements for on-board software that is run on the MOSAR demonstrator SVC platform, SMs and WM for control and management of the system.

3.8.1 F100: Functional requirements [FuncR]
<table><tr><td rowspan=1 colspan=1>FuncR_F101</td><td rowspan=1 colspan=3>Extension of TASTE for reconfigurable systems</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The TASTE framework shall be extended to support modelling and code generation forsoftware systems that can switch between different configurations known at design time.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>ELLI, UBREST, GMV</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_F102</td><td rowspan=1 colspan=3>TASTE-DDS bridge</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>A middleware bridge generator that enables the communication between TASTE andDDS in runtime should be developed in order to assess the capabilities of the softwareand modelling environment needed to support the reconfiguration of an onboard systemwith configurations not known at design time.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>ELLI, UBREST, GMV</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_F103</td><td rowspan=1 colspan=3>DDS over SpaceWire</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>An existing open DDS implementation should be adapted to run over SpaceWire linksso that it can be deployed in the MOSAR demonstrator.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Feasibility needs to be assessed</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>FuncR_F104</td><td rowspan=1 colspan=3>Large data transfer over SpaceWire</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The software should provide a common mechanism to transfer large data messages(1KiB to 1MiB) over SpaceWire links, in order to transfer images from the camerasensor to the OBC and the ground system.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV, TAS-F, USTRAT, SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Feasibility needs to be assessed</td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_F105</td><td rowspan=1 colspan=3>ERGO robotic arm driver for WM</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>A robotic arm driver component shall be developed to execute the robot plan actions onthe WM and return the observations needed by the Agent to manage the execution ofthe plan.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV, DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>FuncR_F106</td><td rowspan=1 colspan=3>ERGO Agent for plan execution</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>An instance of the ERGO Agent shall be deployed on the OBC to command and monitorthe execution of the robotic reconfiguration plan generated on ground.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## 3.8.2 F200: Performance requirements [PerfR] N./A.

3.8.3 F300: Interface requirements [IntR]
<table><tr><td rowspan=1 colspan=1>IntR_F301</td><td rowspan=1 colspan=3>PUS services</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The monitoring and control from the ground system of the onboard system status andthe execution of the robotic reconfiguration plan shall be done using the ESROCOSPUS services library, extended with mission-specific services.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

3.8.4 F400: Design requirements [DesR]
<table><tr><td rowspan=1 colspan=1>DesR_F401</td><td rowspan=1 colspan=3>Robotics data types</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The data types used for the interface between the ERGO Agent and the FunctionalLayer shall be modelled in ASN.1. If a suitable data type is available from ESROCOS, itshould be reused rather than defining a new data type.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## 3.8.5 F500: Physical and resource requirements [PhyR]

N./A.

3.8.6 F600: Environmental and Operational requirements [OpR]
<table><tr><td rowspan=1 colspan=1>OpR_F601</td><td rowspan=1 colspan=3>Plan execution monitoring</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>A graphical tool shall allow the operator to command and monitor the execution of therobotic reconfiguration plan, both simulated and onboard.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Operational Concept RD3Demonstrator preliminary Concept</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## 3.8.7 F700: Safety requirements [SafR] N./A.

## MOSAR - System Requirements Document

3.8.8 F800: Configuration and implementation requirements [ConfR]
<table><tr><td rowspan=1 colspan=1>ConfR_F801</td><td rowspan=1 colspan=3>TASTE modelling</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The TASTE framework shall be used to model the software components running on theOBC. These components include:Functions related to robot autonomy (ERGO Agent and functional layer)Sample OBSW for the management of the reconfigurable system (monitoringand control of the SM)</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>OG1-5 Review RD1</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>ConfR_F802</td><td rowspan=1 colspan=3>Development platform</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The development platform for the OBSW shall be Ubuntu Linux 18.04 LTS (64 bit) on x86.The ESROCOS framework, and in particular TASTE, shall be adapted to run on thisplatform.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>GMV</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

3.9 Validation Requirements [Gxxx]
<table><tr><td rowspan=1 colspan=1>VerR_G101</td><td rowspan=1 colspan=3>Validation purpose</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The MOSAR demonstrator shall allow to verify and validate the following functionalitiesrelevant for future modular spacecraft missions:Creation of a re-configuration execution plan (FuncR_S105)Simulation of the execution plan(FuncR_S106)Manipulation and repositioning of SM (FuncR_S101)Control and re-location of the WM (FuncR_S104, FuncR_S107)Update/upgrade of satellite functionalities (FuncR_S102)Data and power transfer between SMHeat management between SM (FuncR_S115)Failure detection and handling (FuncR_S111)Resources re-allocation, data and power routing (FuncR_S110)</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Testing</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Mission Analysis RD2</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>VerR_G102</td><td rowspan=1 colspan=3>Validation sequence</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The validation shall include the following sequence:1.Calibrate/verify the simulation tool2.Simulate the reconfiguration process and generate a valid robot execution plan3.Execute the plan on the demonstrator setup</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Guidelines AD1 OG9-R14</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS, DLR</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>VerR_G103</td><td rowspan=1 colspan=3>SM modules selection</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The SM implemented in the MOSAR demonstrator should be representative of relevantmodules for future modular spacecraft missions.</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Review of Design</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Mission Analysis RD2</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SITAEL, TAS-Fs</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>VerR_G104</td><td rowspan=1 colspan=3>Orbital Test Facility</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The demonstrator shall be integrated in an orbital simulation facility to validate theMOSAR scenarios</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Inspection</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>Guidelines AD1 OG9-R13Guidelines AD1 OG9-R14</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>The orbital dynamics is not relevant in OG9 – e.g. docking is not part of the scenarios.The provided facility (in SPACEAPPS&#x27; lab) could however produce illuminationconditions that are relevant w.r.t. orbital applications (if relevant)</td></tr></table>

<table><tr><td rowspan=1 colspan=1>VerR_G105</td><td rowspan=1 colspan=3>Test facility dimensions</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The test facility shall ensure a volume of 5 m (L)x 3.5 m (W)x 3 m (H) in orderto allow the integration of the test bench and all required components for theregular performance of the demonstration</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Inspection</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Demonstrator</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>Values TBC by PDR</td></tr></table>

<table><tr><td rowspan=1 colspan=1>VerR_G106</td><td rowspan=1 colspan=3>Test facility displays</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The test facility shall provide displays to support the design and monitoring ofthe execution plan</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Inspection</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Demonstrator</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3></td></tr></table>

<table><tr><td rowspan=1 colspan=1>VerR_G107</td><td rowspan=1 colspan=3>Test facility power</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The test facility shall provide the required power for the performance of thedemonstration</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Inspection</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Demonstrator</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>It can include barrier protections, flashing light during operations,</td></tr></table>

## MOSAR - System Requirements Document

<table><tr><td rowspan=1 colspan=1>VerR_G108</td><td rowspan=1 colspan=3>Test facility safety features</td></tr><tr><td rowspan=1 colspan=1>STATEMENT</td><td rowspan=1 colspan=3>The test facility shall provide safety features to guarantee the safe operation ofthe demonstrator</td></tr><tr><td rowspan=1 colspan=1>VERIFICATION</td><td rowspan=1 colspan=1>Inspection</td><td rowspan=1 colspan=1>COVERS</td><td rowspan=1 colspan=1>MOSAR Demonstrator</td></tr><tr><td rowspan=1 colspan=1>RESPONSIBLE</td><td rowspan=1 colspan=3>SPACEAPPS</td></tr><tr><td rowspan=1 colspan=1>COMMENT</td><td rowspan=1 colspan=3>It can include barrier protections, flashing light during operations,</td></tr></table>