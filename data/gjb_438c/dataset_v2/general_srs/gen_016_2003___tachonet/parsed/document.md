N.V. Getronics Belgium S.A.

Rue de Genèvestraat 10

1140 BRUXELLES/BRUSSEL

 (32) 2 229.91.11

DG TREN

## TACHOnet

## Software Requirements Specification

01\_00

21-Feb-03

## Document Approval

<table><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1>NAME</td><td rowspan=1 colspan=1>DATE</td><td rowspan=1 colspan=1>SIGNATURE</td></tr><tr><td rowspan=1 colspan=1>Prepared by:</td><td rowspan=1 colspan=1>F. Silvestre</td><td rowspan=1 colspan=1>21-Feb-03</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Checked by:</td><td rowspan=1 colspan=1>Ph. Francis</td><td rowspan=1 colspan=1>21-Feb-03</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Quality control by:</td><td rowspan=1 colspan=1>P. Delmée</td><td rowspan=1 colspan=1>21-Feb-03</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Approved by:</td><td rowspan=1 colspan=1>Yves Hardy(DG TREN)</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr></table>

## Distribution List

<table><tr><td rowspan=1 colspan=1>COMPANY</td><td rowspan=1 colspan=1>NAME</td><td rowspan=1 colspan=1>FUNCTION</td><td rowspan=1 colspan=1>FOR INFO / APPROVAL</td></tr><tr><td rowspan=1 colspan=1>DG TREN</td><td rowspan=1 colspan=1>Y. Hardy</td><td rowspan=1 colspan=1>Project Manager</td><td rowspan=1 colspan=1>Approval</td></tr><tr><td rowspan=1 colspan=1>Getronics</td><td rowspan=1 colspan=1>P. Delmée</td><td rowspan=1 colspan=1>Project Manager</td><td rowspan=1 colspan=1>Info</td></tr><tr><td rowspan=1 colspan=1>Getronics</td><td rowspan=1 colspan=1>Ph. Francis</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Getronics</td><td rowspan=1 colspan=1>W. Van Acker</td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr></table>

## Change Control History

<table><tr><td rowspan=1 colspan=1>VERSION</td><td rowspan=1 colspan=1>DATE</td><td rowspan=1 colspan=1>AUTHOR</td><td rowspan=1 colspan=1>DESCRIPTION</td><td rowspan=1 colspan=1>PARAGRAPHS</td></tr><tr><td rowspan=1 colspan=1>00_01</td><td rowspan=1 colspan=1>04-Dec-03</td><td rowspan=1 colspan=1>F. Silvestre</td><td rowspan=1 colspan=1>Original issue</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>01_00</td><td rowspan=1 colspan=1>21-Feb-03</td><td rowspan=1 colspan=1>F. Silvestre</td><td rowspan=1 colspan=1>Release iteration C1</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr></table>

## Document information

<table><tr><td rowspan=1 colspan=1>CREATION DATE:</td><td rowspan=1 colspan=1>04-Dec-03</td></tr><tr><td rowspan=1 colspan=1>FILENAME:</td><td rowspan=1 colspan=1>TCN-SRS-01 00-EN.doc</td></tr><tr><td rowspan=1 colspan=1>LOCATION:</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>NUMBER OF PAGES:</td><td rowspan=1 colspan=1>76</td></tr><tr><td rowspan=1 colspan=1></td><td rowspan=1 colspan=1></td></tr></table>

## CONTENTS

Introduction ....   
Chapter 1: Requirements ......   
Overview .   
Types of Requirements.... .6   
List of Functional Requirements . .10   
List of Non-functional Requirements.. .12   
Chapter 2: Use-Case Model .. ..15   
Overview .. .15   
Introduction . .16   
Actor Catalog . .17   
Use Case Catalog . .18   
Section 2.1 - Use Case Package “TCN Administrative Tasks” ..20   
Overview .... .20   
Use Case 01 – Check driver(s)’ issued cards .22   
Use Case 02 – Check tachograph card status .25   
Use Case 03 – Declaration of card status modification.. ..28   
Use Case 04 – Send Card/Driving License Assignment . .32   
Use Case 05 – Get Phonex Search Keys .... ..35   
Use Case 06 – Get US/Ascii Transliteration . .37   
Section 2.2 - Use Case Package “TCN Statistics Tasks”. .39   
Overview . .39   
Use Case 07 – “Add a new CIA” .40   
Use Case 08 – “Reset Password” .42   
Use Case 09 – “Generate Statistics” .44   
Use Case 10 – “Browse Statistics” .47   
Use Case 11 – Log the message .. .52   
Section 2.3 - Use Case Package “TCN System Tasks” ..53   
Overview ..... .53   
Use-Case 12 – “Monitor the system” ..54   
Use-Case 13 – “Manage Member State”. ..55

## Introduction

## Purpose

This document aims at capturing the complete software requirements for the system. It fully describes the external behaviour of the application(s) or subsystem(s) identified. It also describes non-functional requirements, design constraints and other factors necessary to provide a complete and comprehensive description of the requirements for the software.

The current version of this document is the one released at end of iteration C1.

## References

The present document makes references to the following documents:

\- [1] Specific Agreement n°36 under framework contract n° DI/02450-00 – 13- Nov-03

\- [2] TCN XML Messaging Reference Guide V1.40.

\- [3] Card Issuing Working Group – General Report – URBA 2000.

## Abbreviations

\- CIA – Card Issuing Authority

\- MS – Member State

\- SPOC – Single Point Of Contact

\- TCN – TACHOnet

## Structure of the document

The first chapter describes the functional and non-functional requirements. The second chapter describes the use-case model comprehensively, in terms of how the model is structured into packages and what use cases and actors are in the model.

## Chapter 1: Requirements

## Overview

Introduction This chapter describes the different requirements (functional and non-functional).

Contents This chapter contains the following topics.

<table><tr><td rowspan=1 colspan=1>Topic</td><td rowspan=1 colspan=1>See Page</td></tr><tr><td rowspan=1 colspan=1>Types of Requirements</td><td rowspan=1 colspan=1>6</td></tr><tr><td rowspan=1 colspan=1>List of Functional Requirements</td><td rowspan=1 colspan=1>10</td></tr><tr><td rowspan=1 colspan=1>List of Non-functional Requirements</td><td rowspan=1 colspan=1>12</td></tr></table>

## Types of Requirements

## Definition

A requirement is defined as "a condition or capability to which a system must conform".

Functional requirements specify actions that a system must be able to perform, without taking physical constraints into consideration. These are often best described in a use-case model and in use cases. Functional requirements thus specify the input and output behaviour of a system.

Requirements that are not functional are sometimes called non-functional requirements. Many requirements are non-functional, and describe only attributes of the system or attributes of the system environment.

## FURPS+

There are a many different kinds of requirements. One way of categorizing them is described as the FURPS+ model [GRA92], using the acronym FURPS to describe the major categories of requirements with subcategories as shown below.

\- Functionality,

\- Usability,

\- Reliability,

\- Performance and

\- Supportability

The "+" in FURPS+ helps you to also remember to also include such requirements as

\- design constraints,

\- interface requirements and

\- physical requirements.

## Functionality (FUN)

Functional requirements may include:

\- feature sets,

\- capabilities, and

\- security.

Continued on next page

## Types of Requirements, Continued

Usability (USA) Usability requirements may include such sub-categories as:

\- human factors,

\- aesthetics,

\- consistency in the user interface,

\- online and context-sensitive help,

\- wizards and agents,

\- user documentation, and

\- training materials.

## Reliability (REL)

Reliability requirements to be considered are:

\- Availability (percentage of time available, hours of use, maintenance access,…)

\- frequency / severity of failure,

\- recoverability,

\- predictability,

\- accuracy, and

\- mean time between failure (MTBF).

## Performance(PER)

A performance requirement imposes conditions on functional requirements. For example, for a given action, it may specify performance parameters for:

\- throughput (e.g. transactions per second),

\- response time,

\- recovery time, or

\- resource usage (memory, disk, cpu,…).

Continued on next page

## Types of Requirements, Continued

## Supportability (SUP)

Supportability requirements may include:

\- testability,

\- extensibility,

\- adaptability,

\- maintainability,

\- compatibility,

\- configurability,

\- serviceability,

\- installability, or

\- localizability (internationalization).

## Design Requirement (DES)

A design requirement, often called a design constraint, specifies or constrains the design of a system.

This section should indicate any design constraints on the system being built. Design constraints represent design decisions that have been mandated and must be adhered to. Examples include software languages, software process requirements, prescribed use of developmental tools, architectural and design constraints, purchased components, class libraries, etc.

## Interface Requirement (INT)

This section defines the interfaces that must be supported by the application. It should contain adequate specificity, protocols, ports and logical addresses, etc., so that the software can be developed and verified against the interface requirements.

An interface requirement may be classified into:

\- User interface (user interfaces that are to be implemented by the software)

Hardware interface (hardware interfaces that are to be supported by the software, including logical structure, physical addresses, expected behavior, etc.)

Software interface (software interfaces to other components of the software system. These may be purchased components, components reused from another application or components being developed for subsystems outside of the scope of this project, but with which this software application must interact).

## Types of Requirements, Continued

A physical requirement specifies a physical characteristic that a system must possess; for example,

\- material,

\- shape,

\- size, and

\- weight.

This type of requirement can be used to represent hardware requirements, such as

\- the physical network configurations required

This section describes by reference any applicable standards and the specific sections of any such standards that apply to the system being described. For example, this could include legal, quality and regulatory standards, industry standards for usability, interoperability, internationalization, operating system compliance, etc.

## List of Functional Requirements

## Introduction

Functional requirements specify actions that a system must be able to perform, without taking physical constraints into consideration. Functional requirements thus specify the input and output behaviour of a system.

A list of these functional requirements is given below with an identification and a short description for each of them.

These functional requirements are best described once translated into use cases (see Use Case Model chapter).

Each identified functional requirement is assigned a unique key “FUN-nn” where nn is a sequence number identifying the functional requirement. The table hereafter lists all the functional requirements :

<table><tr><td rowspan=1 colspan=1>FunctionalRequirementId</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>FUN-01</td><td rowspan=1 colspan=1>The system must allow a member of the network to send requeststo a particular or all the other members about possible delivery ofa driver&#x27;s smart card to a similar person.</td></tr><tr><td rowspan=1 colspan=1>FUN-02</td><td rowspan=1 colspan=1>The system must allow a member of the network to send a bulkrequest on all or a large part of its driver&#x27;s smart card holders to aparticular or all members of the network.</td></tr><tr><td rowspan=1 colspan=1>FUN-03</td><td rowspan=1 colspan=1>The system must allow a member to do statistics on messagesissued and received from/to his system.</td></tr><tr><td rowspan=1 colspan=1>FUN-04</td><td rowspan=1 colspan=1>The system must provide automatic reply to the sender of therequest through the use of a standard interface to the Memberssystems.</td></tr><tr><td rowspan=1 colspan=1>FUN-05</td><td rowspan=1 colspan=1>The system must track the workflow between senders and relatedreplies.</td></tr><tr><td rowspan=1 colspan=1>FUN-06</td><td rowspan=1 colspan=1>The system must be able, in accordance with the rules on delaysfor each transaction, to automatically transmit alert messages tosenders/replier/administrator when, f.i. a constraint on delay forreply is not fulfilled.</td></tr><tr><td rowspan=1 colspan=1>FUN-07</td><td rowspan=1 colspan=1>The system must allow the administrator to extract statistics ofuse, standard delay of reply by member/period, percentage ofunsuccessful transaction,... .</td></tr><tr><td rowspan=1 colspan=1>FUN-08</td><td rowspan=1 colspan=1>The system must provide the management of user rights andpermissions.</td></tr><tr><td rowspan=1 colspan=1>FUN-09</td><td rowspan=1 colspan=1>The system must be able to define and manage various type ofmessages already in the driver&#x27;s smart card holder like pre-delivery check, stolen/lost cards, renewals, exchanges andduplicates.</td></tr><tr><td rowspan=1 colspan=1>FUN-10</td><td rowspan=1 colspan=1>The system must be able to include new members in the networkthrough simple administrative tasks.</td></tr></table>

## List of Functional Requirements, Continued

List of functional requirements (continued)

<table><tr><td rowspan=1 colspan=1>FunctionalRequirementId</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>FUN-11</td><td rowspan=1 colspan=1>The system must be highly automatic to relieve the users of asmany repetitive and tedious tasks as possible.</td></tr><tr><td rowspan=1 colspan=1>FUN-12</td><td rowspan=1 colspan=1>The system must provide at application level a full security(including non repudiation) and encryption policy compatiblewith the level of security required in such situation.</td></tr><tr><td rowspan=1 colspan=1>FUN-13</td><td rowspan=1 colspan=1>The system must guarantee that none of the Member of thenetwork, including the administrator, is technically able to reconstruct a consolidated European database through the use ofthe messages exchanged.The system must be such that none of the Member States of thenetwork, including the administrator, re-construct a consolidatedEuropean database.</td></tr><tr><td rowspan=1 colspan=1>FUN-14</td><td rowspan=1 colspan=1>The system must allow a Member State (through its Card IssuingAuthority) to ask for the status of card (lost, stolen,...) to thecorresponding Card Issuing Authority of the Member Statehaving issued the card.</td></tr><tr><td rowspan=1 colspan=1>FUN-15</td><td rowspan=1 colspan=1>The system must allow a Member State (through its Card IssuingAuthority) to send card status modification requests (lost,stolen,...) to the corresponding Card Issuing Authority of theMember State having issued the card.</td></tr><tr><td rowspan=1 colspan=1>FUN-16</td><td rowspan=1 colspan=1>The system must allow enforcement authorities (through its CardIssuing Authority) to ask for driver&#x27;s card status (based on eithercard number + issuing Member State code or driver&#x27;s surname,first names, date of birth and issuing Member State code) to thecorresponding Card Issuing Authority of the Member Statehaving issued the card.</td></tr><tr><td rowspan=1 colspan=1>FUN-17</td><td rowspan=1 colspan=1>The system must allow enforcement authorities (through its CardIssuing Authority) to ask for workshop card status (based onworkshop card number + issuing Member State code) to thecorresponding Card Issuing Authority of the Member Statehaving issued the card.</td></tr></table>

## List of Non-functional Requirements

## Introduction

Non-functional requirements describe only attributes of the system or attributes of the system environment.

Each identified non-functional requirement is assigned a unique key “XXX-nn” where XXX identifies the type of requirement (e.g. PER for performance requirement) and nn is a sequence number identifying the non-functional requirement.

## Usability requirements

The table hereafter lists all the non-functional “usability” requirements :

<table><tr><td rowspan=1 colspan=1>UsabilityRequirementId</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>USA-01</td><td rowspan=1 colspan=1>The system must guide users through an interface based on enduser concepts.</td></tr><tr><td rowspan=1 colspan=1>USA-02</td><td rowspan=1 colspan=1>The system must be easy to learn and does not obstruct thethematic understanding of the users.</td></tr><tr><td rowspan=1 colspan=1>USA-03</td><td rowspan=1 colspan=1>The system must make it easy to correct mistakes.</td></tr></table>

The table hereafter lists all the non-functional “reliability” requirements:

<table><tr><td rowspan=1 colspan=1>ReliabilityRequirementId</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>REL-01</td><td rowspan=1 colspan=1>The system is to be designed as a robust and dependableoperational system which is tolerant to operator errors andwhich will recover cleanly from power cuts or other disasters.</td></tr><tr><td rowspan=1 colspan=1>REL-02</td><td rowspan=1 colspan=1>The system must function reliably, with few or no interruptionsin its first operational year and fewer still thereafter.</td></tr><tr><td rowspan=1 colspan=1>REL-03</td><td rowspan=1 colspan=1>The system must give stable and reproducible results.</td></tr></table>

## List of Non-functional Requirements, Continued

## Performance requirements

The table hereafter lists all the non-functional “performance” requirements:

<table><tr><td rowspan=1 colspan=1>PerformanceRequirementId</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>PER-01</td><td rowspan=1 colspan=1>The system should be able to cover more than one contact pointper country depending on the administrative organisationadopted by each country and able to work in a multihierarchical environment. This is no longer the case sinceeverybody agrees upon having a single point of contact perMember State (even though the Member State is organized withseveral Card Issuing Authorities – up to the Member State tomanage its own organisation).</td></tr><tr><td rowspan=1 colspan=1>PER-02</td><td rowspan=1 colspan=1>There will be no restriction in time or place for the use of thesoftware built from the specifications produced under thiscontract.</td></tr><tr><td rowspan=1 colspan=1>PER-03</td><td rowspan=1 colspan=1>The system must be able to establish and keep the dialog withthe Members systems despite the various technicalenvironments and technologies used on their sites.</td></tr><tr><td rowspan=1 colspan=1>PER-04</td><td rowspan=1 colspan=1>The system will be designed so that background tasks cancontinue while the user performs foreground tasks.</td></tr><tr><td rowspan=1 colspan=1>PER-05</td><td rowspan=1 colspan=1>The system will be used 24x7 by operators under pressure toproduce results rapidly. The system must respond rapidly touser requests irrespective of any background tasks. Such high-availability (24x7) is also required from the Member Statessystems to ensure acceptable response time (less than 1 minute)to enforcement authorities requests.</td></tr></table>

The table hereafter lists all the non-functional “supportability” requirements:

<table><tr><td rowspan=1 colspan=1>SupportabilityRequirementId</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>SUP-01</td><td rowspan=1 colspan=1>The system should be able to support other types of messagestructure to cover f.i. a future driving licence network andcorrelated activities.</td></tr><tr><td rowspan=1 colspan=1>SUP-02</td><td rowspan=1 colspan=1>The system must be maintainable and extensible.</td></tr><tr><td rowspan=1 colspan=1>SUP-03</td><td rowspan=1 colspan=1>The system must be designed so that it can migrate to upgradedhardware or new versions of the operating systems involved.</td></tr><tr><td rowspan=1 colspan=1>SUP-04</td><td rowspan=1 colspan=1>The system must be able to migrate to other type of networkthan the one proposed by TESTA-II.</td></tr><tr><td rowspan=1 colspan=1>SUP-05</td><td rowspan=1 colspan=1>The system must provide solutions/rules regarding dataencoding problems such as supporting different character sets,name truncation rules, name matching in case of misspelling,...</td></tr></table>

## List of Non-functional Requirements, Continued

The table hereafter lists all the non-functional “design” requirements:

<table><tr><td rowspan=1 colspan=1>DesignRequirementId</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>DES-01</td><td rowspan=1 colspan=1>The system must be designed and documented with theexpectation that its operational lifetime will be many years.</td></tr><tr><td rowspan=1 colspan=1>DES-02</td><td rowspan=1 colspan=1>Each Member of this network will organise its data about smartcard holders with no constraints or recommendations onoperating system and/or technology used. The system will beable to dialog with these environments or specify a genericinterface to dialog with the Member&#x27;s applications.</td></tr></table>

The table hereafter lists all the non-functional “implementation” requirements:

<table><tr><td>Implementation Requirement Id</td><td>Description</td></tr><tr><td>IMP-01</td><td></td></tr></table>

The table hereafter lists all the non-functional “interface” requirements:

<table><tr><td rowspan=1 colspan=1>InterfaceRequirementId</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>INT-01</td><td rowspan=1 colspan=1>The system must use the network facilities supplied by theTESTA-II network.</td></tr><tr><td rowspan=1 colspan=1>INT-02</td><td rowspan=1 colspan=1>The algorithms in the software will be based on existingtechniques and no research will be required to develop newalgorithms under this contract.</td></tr><tr><td rowspan=1 colspan=1>INT-03</td><td rowspan=1 colspan=1>Most of the functionality of the new software shall depend onpre-existing or commercially available software.</td></tr></table>

The table hereafter lists all the non-functional “physical” requirements:

<table><tr><td>Physical Requirement Id</td><td>Description</td></tr><tr><td>HAR-01</td><td>-</td></tr></table>

## Chapter 2: Use-Case Model

## Overview

## Introduction

This chapter describes the use-case model comprehensively, in terms of how the model is structured into packages and what use cases and actors are in the model.

## Contents

This chapter contains the following topics:

<table><tr><td rowspan=1 colspan=1>Topic</td><td rowspan=1 colspan=1>See Page</td></tr><tr><td rowspan=1 colspan=1>Introduction</td><td rowspan=1 colspan=1>16</td></tr><tr><td rowspan=1 colspan=1>Actor Catalog</td><td rowspan=1 colspan=1>17</td></tr><tr><td rowspan=1 colspan=1>Use Case Catalog</td><td rowspan=1 colspan=1>18</td></tr><tr><td rowspan=1 colspan=1>Use Case Package “TCN Administrative Tasks&quot;</td><td rowspan=1 colspan=1>20</td></tr><tr><td rowspan=1 colspan=1>Use Case Package “TCN Statistics Tasks&quot;</td><td rowspan=1 colspan=1>39</td></tr><tr><td rowspan=1 colspan=1>Use Case Package “TCN System Tasks&quot;</td><td rowspan=1 colspan=1>53</td></tr></table>

## Introduction

A use-case model is a model of the system's intended functions and its surroundings. It serves as a contract between the customer, the users and the system developers on the functionality of the system, which allows :

\- Customers and users to validate that the system will become what they expected.

\- System developers to build what is expected.

The same use-case model is used in system analysis, design, implementation, and testing.

The use-case model consists of use cases and actors.

An actor defines a coherent set of roles that users of the system can play when interacting with it. A user can either be an individual or an external system.

A use case defines a set of use-case instances, where each instance is a sequence of actions a system performs that yields an observable result of value to a particular actor. Each use case in the model is described in detail, showing step-by-step how the system interacts with the actors, and what the system does in the use case. Use cases function as a unifying thread throughout the software lifecycle.

## Actor Catalog

<table><tr><td></td><td colspan="2">This map describes the list of identified actors.</td></tr><tr><td>Introduction</td><td colspan="2">The following figure describes the different actors:</td></tr><tr><td>List of actors</td><td colspan="2">TACHOnet considers a whole CIA (Card Issuing Authority) as a single user (the CIA administrator excepted) through the CIA application, in charge of exchanging XML messages with TACHOnet. TACHOnet does not manage CIA users working with the CIA application (e.g. the clerks or enforcers performing administrative tasks). These latter ones have to be managed accordingly by</td></tr><tr><td colspan="2"></td><td>From the TACHOnet viewpoint, the ClA application acts as a single user and will be defined accordingly (a single digital certificate will be delivered for a ClA application). Therefore, enforcers are also considered as ClA users who should then be managed by each Member State (TACHOnet only have a SPOC CIA). A ClA Application will be granted the rights for carrying out any of the administrative tasks (see Administrative tasks for more details).</td></tr><tr><td colspan="2">enforcers) may have aœess to a web appl ication providing a user inte face on top of the <img src="images/0eac3f570026402fff53717bc2299d5dcfa4c4d8fb00f5170ac7fdfa4605499b.jpg"/> A CIA Administrator is a single user who isin charge of administering the CIA application (exchanging XML messages with TACHOnet) in a Member State.</td><td>TACHOnet web se rvcices (phonex and transliterati on).</td></tr><tr><td colspan="2"><img src="images/340af4f61f17d88fb9deb87a55a94885eb2dfd4b0fa57b5eb3400ae295b1de47.jpg"/> From the TACHOnet viewpoint, the ClA Administrator will be assigned an account and will be services in terms of configuration, performance, logging, tracking,... <img src="images/eb953209cd7a091389a8faf12f56a92eb4d4361deea402250910ca4d72bc2520.jpg"/> The TCN Administrator is not related to any CIA and works for the EC or Trusted Third Party</td><td>granted the rights to browse the TCN usage statistics reports through a secure web site. The TCN (TACHOnet) Administrator is in charge of administering the whole TACHOnet</td></tr></table>

Figure 1 – List of Actors

## Use Case Catalog

Introduction

This map describes the list of identified use cases. For clarity reasons, use cases are organized as packages. The description of each of the use cases packages is given in the next sections.

Use Case Model The following figure outlines the actors and use cases of the TACHOnet system: Diagram

TACHOnet Administrative Tasks

![](images/7e58348ec7ea5f662b5e0e72046e947c2832479cfb0bec0e8acb10a63b91002a.jpg)  
Figure 2 – Use Case Model Diagram

## Use Case Catalog, Continued

For organizational purposes, use cases are gathered in packages. The list of the TCN Use Case Packages is outlined in the following diagram:

![](images/0fd43ae33f042732ebd661dcfb4335e3f094973a85dcb470844a5dca293c9add.jpg)  
Figure 3 – List of Use Case Packages

The table hereafter lists all the use cases along with their assigned id:

<table><tr><td rowspan=1 colspan=1>The UC Package...</td><td rowspan=1 colspan=1>Contains the following Use Cases...</td></tr><tr><td rowspan=1 colspan=1>TCN AdministrativeTasks</td><td rowspan=1 colspan=1>Check Driver&#x27;s Issued CardsCheck Tachograph Card StatusDeclaration of Card Status ModificationSend card/Driving License AssignmentGet Phonex Search KeysGet US/Ascii Transliteration</td></tr><tr><td rowspan=1 colspan=1>TCN Statistics Tasks</td><td rowspan=1 colspan=1>Add a new CIAReset PasswordBrowse StatisticsGenerate StatisticsLog the message</td></tr><tr><td rowspan=1 colspan=1>TCN System Tasks</td><td rowspan=1 colspan=1>Monitor the systemManage Member State</td></tr></table>

## Section 2.1 - Use Case Package “TCN Administrative Tasks” Overview

This section describes the use cases related to the “TCN Administrative Tasks” package. The following diagram gives a high-level view of the use cases of this package:

![](images/e0c7fcbc358b267dbb0222c3b106563f34d726de718875d1e8cb1542af8277d9.jpg)  
Figure 4 –Use Case Package “TCN Administrative Tasks”

## Overview, Continued

## Contents

This section contains the following topics:

<table><tr><td rowspan=1 colspan=1>Topic</td><td rowspan=1 colspan=1>See Page</td></tr><tr><td rowspan=1 colspan=1>Use Case 01 – Check driver(s)’ issued cards</td><td rowspan=1 colspan=1>22</td></tr><tr><td rowspan=1 colspan=1>Use Case 02 – Check tachograph card status</td><td rowspan=1 colspan=1>25</td></tr><tr><td rowspan=1 colspan=1>Use Case 03 – Declaration of card status modification</td><td rowspan=1 colspan=1>28</td></tr><tr><td rowspan=1 colspan=1>Use Case 04 – Send Card/Driving License Assignment</td><td rowspan=1 colspan=1>32</td></tr><tr><td rowspan=1 colspan=1>Use Case 05 – Get Phonex Search Keys</td><td rowspan=1 colspan=1>35</td></tr><tr><td rowspan=1 colspan=1>Use Case 06 – Get US/Ascii Transliteration</td><td rowspan=1 colspan=1>37</td></tr></table>

## Use Case 01 – Check driver(s)’ issued cards

## Description

This use case consists of processing a request for checking driver’s issued card coming from a Card Issuing Authority (CIA). Such request could contain the data for a single driver (online mode) or several drivers (batch mode).

This use case is also used by enforcers (on behalf of CIA – as TACHOnet only sees CIA as SPOC) during road checks.

## Basic flow

The basic flow consists of the following steps:

<table><tr><td rowspan=1 colspan=1>Step</td><td rowspan=1 colspan=1>Action</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>TACHOnet deciphers the received request and logs the received requestas-is in its tracking database.</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>TACHOnet validates its syntax and assigns it a TACHOnet refid(TCNRefId).</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>TACHOnet will build as many new requests as issuing Member Statecodes identified in the original request (+ another one for all sub-requests not mentioning any issuing Member State code) by applyingdefined name encoding rules to the given surname(s) and first name(s) inorder to compute the search keys.</td></tr><tr><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>For each issuing Member State identified (if any) in the original request,TACHOnet builds, logs and encrypts a new request (only containingsub-requests for the corresponding issuing Member State), sends it to thecorresponding Member State&#x27;s CIA application and waits for receivingthe response.For the sub-request mentioning any issuing Member State code (if any),TACHOnet builds, logs and encrypts a new request (only containingsub-requests not mentioning any issuing Member State), broadcasts it toall the Member States configured in TACHOnet (except the MemberState having sent the original request) and waits for receiving eachresponse.</td></tr><tr><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>For each received response, TACHOnet deciphers it, logs it as-is in itstracking database and validates its syntax. If it is valid, TACHOnetstores the response data (linked to the TCN refid) in the database (forlater building the single consolidated response that TACHOnet will sendwhen all responses are received or when the timeout is reached).</td></tr><tr><td rowspan=1 colspan=1>6</td><td rowspan=1 colspan=1>When all responses are received or when the timeout is reached,TACHOnet builds, from the received responses stored in its database,the single consolidated response.</td></tr><tr><td rowspan=1 colspan=1>7</td><td rowspan=1 colspan=1>TACHOnet logs the consolidated response is in its tracking database,encrypts it and sends it to the original caller.</td></tr></table>

## Use Case 01 – Check driver(s)’ issued cards, Continued

Several alternate flows may exist depending on the result of some events/actions of the basic flow:

<table><tr><td rowspan=1 colspan=1>Alternateflow</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>ALT-01</td><td rowspan=1 colspan=1>When TACHOnet receives a negative response from a Member StateCIA, it should log it and consider the request sent to that MemberState CIA as completed (with error).</td></tr><tr><td rowspan=1 colspan=1>ALT-02</td><td rowspan=1 colspan=1>When TACHOnet receives multiple responses (corresponding to asingle request) from a Member State CIA, it should ignore thesuperfluous additional responses. The first received response is theprocessed one.</td></tr><tr><td rowspan=1 colspan=1>ALT-03</td><td rowspan=1 colspan=1>When TACHOnet doesn&#x27;t receive within time a Member State CIAresponse, it should mention ‘timeout&#x27; as status code for that MemberState CIA in the consolidated response.</td></tr><tr><td rowspan=1 colspan=1>ALT-04</td><td rowspan=1 colspan=1>When TACHOnet receives a late Member State CIA response, itshould log it and ignore it.</td></tr><tr><td rowspan=1 colspan=1>ALT-05</td><td rowspan=1 colspan=1>When TACHOnet receives a syntactically invalid request / response,it should always send back a negative receipt with Invalid Formatrequest’ as status code and warn the TCN Administrator.</td></tr><tr><td rowspan=1 colspan=1>ALT-06</td><td rowspan=1 colspan=1>When TACHOnet receives an invalid XML message (request,response), it will respond with a negative receipt mentioning thereason (invalid format).</td></tr></table>

## Special requirements

• Non-repudiation of transaction must be guaranteed

• Data privacy must also be guaranteed

• All Member State CIAs must provide services (using proposed messages formats below and proposed technical rules in [2]) for:

• Sending a request for checking driver’s issued cards to TACHOnet

• Receiving and handling a TACHOnet request for checking driver’s issued cards

• Sending TACHOnet a response to such TACHOnet request (asynchronous)

• Receiving and handling a TACHOnet response to original request for checking driver’s issued cards (asynchronous)

## Pre-conditions

• The CIA requesting the check must be defined in TACHOnet

• The CIA requesting the check must send its request using the TACHOnet required request format (see below)

## Post-conditions

• The CIA requesting the check has received a response to its request.

## Use Case 01 – Check driver(s)’ issued cards, Continued

• A CIA application (named CIA) requesting the check (CIA’s clerk or enforcer)

• All CIA applications (named CIAs) to which TACHOnet will broadcast the request

• The TACHOnet system

The following diagram outlines the flow of messages exchanged between actors:

![](images/51a21ceb1edaceccf7e906057a0847e72c499f066f5e24ddbd9ac16ff9c8d650.jpg)  
Figure 5 – UC-01 messages flow

Please refer to [2] for a complete description.

• In case of problems (e.g. network problem,...) when sending a message (request, response), TACHOnet will automatically retry to send it 3 times at regular interval till request timeout. Afterwards, if still unsuccessful, it will record a ‘Server Error’ status code.

## Use Case 02 – Check tachograph card status

## Description

This use case consists of checking the status of a tachograph card based on its card number. This use case is very useful for CIAs in order to check the validity of a card prior to performing some administrative tasks (e.g. to avoid from declaring a lost/stolen card for a wrongly keyed-in card number,...). It is also useful for enforcement authorities during road-checks where workshop could also be checked (beside driver cards).

The checked card is identified by its card number and its issuing Member State code. As an issued card must be unique, it should only exist in a single CIA data store (the CIA having issued the card).

## Basic flow

The basic flow consists of the following steps:
<table><tr><td rowspan=1 colspan=1>Step</td><td rowspan=1 colspan=1>Action</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>TACHOnet deciphers the received request and logs the received requestas-is in its tracking database.</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>TACHOnet validates its syntax and assigns it a TACHOnet refid(TCNRefId).</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>TACHOnet will build as many new requests as issuing Member Statecodes identified in the original request. TACHOnet figures out the targetissuing Member State(s) from the issuing Member State code given foreach to-be-checked card. Every new request only contains cardnumber(s) issued by a particular Member State.</td></tr><tr><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>For each identified issuing Member State(s), TACHOnet builds, logs andencrypts the new request, sends it to it and waits for receiving theresponse.</td></tr><tr><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>For each received response, TACHOnet deciphers it, logs it as-is in itstracking database and validates its syntax. If it&#x27;s valid, TACHOnet storesthe response message (linked to the TCNRefId) in the database (for laterbuilding the single consolidated response that TACHOnet will sendwhen all responses are received or when the timeout is reached).</td></tr><tr><td rowspan=1 colspan=1>6</td><td rowspan=1 colspan=1>When all responses are received or when the timeout is reached,TACHOnet builds, logs and encrypts the consolidated response (fromthe responses received so far), and sends it to the original caller.</td></tr></table>

## Alternate flows

The same alternate flows as described for UC-01 (page 23) may exist depending on the result of some events/actions of the basic flow.

## Use Case 02 – Check tachograph card status, Continued

## Special requirements

• Non-repudiation of transaction must be guaranteed

• Data privacy must also be guaranteed

• All Member State CIAs must provide services (using proposed messages formats below and proposed technical rules in [2]) for:

• Sending a request for checking a card number to TACHOnet

• Receiving and handling a TACHOnet request for checking a card number

• Sending TACHOnet a response to such TACHOnet request (asynchronous)

• Receiving and handling a TACHOnet response to original request for checking a card number (asynchronous)

## Pre-conditions

• The CIA sending the request must be defined in TACHOnet

• The CIA sending the request must send it using the TACHOnet required request format (see below)

## Post-conditions

• The CIA sending the request has received a response to its request.

## Actors

• A CIA requesting the check (CIA’s clerk or enforcer)

• All CIAs to which TACHOnet will broadcast the request

• The TACHOnet system

## XML Messages

Please refer to [2] for a complete description.

Continued on next page

## Use Case 02 – Check tachograph card status, Continued

The following diagram outlines the flow of messages exchanged between actors (assuming a single card number is specified in the original request, meaning TACHOnet has to forward the request to the Member State having issued the card):

![](images/390d10cfd4d95a8a0af83ce11f6530cbee65d37393432cbe00678d2b964f2a44.jpg)  
Figure 6 – UC-03 messages flow

• In case of problems (e.g. network problem,...) when sending a message (request, response), TACHOnet will automatically retry to send it 3 times at regular interval till request timeout. Afterwards, if still unsuccessful, it will record a ‘Server Error’ status code.

## Use Case 03 – Declaration of card status modification

Description

This use case consists of processing a request for declaring the modification of the status of card. It can be asked by CIA clerks or by enforcers.

The following table describes which new card status codes are allowed when declaring a card status modification:

<table><tr><td rowspan=1 colspan=1>Card Status</td><td rowspan=1 colspan=1>MS2TCN_ModCardStatus_Req</td><td rowspan=1 colspan=1>Reason</td></tr><tr><td rowspan=1 colspan=1>Application</td><td rowspan=1 colspan=1>N</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Approved</td><td rowspan=1 colspan=1>N</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Personalised</td><td rowspan=1 colspan=1>N</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Dispatched</td><td rowspan=1 colspan=1>N</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>HandedOver</td><td rowspan=1 colspan=1>Y</td><td rowspan=1 colspan=1>valid again (after wrong declaration)</td></tr><tr><td rowspan=1 colspan=1>Confiscated</td><td rowspan=1 colspan=1>Y</td><td rowspan=1 colspan=1>Confiscation card declaration</td></tr><tr><td rowspan=1 colspan=1>Suspended</td><td rowspan=1 colspan=1>Y</td><td rowspan=1 colspan=1>Suspended card declaration</td></tr><tr><td rowspan=1 colspan=1>Withdrawn</td><td rowspan=1 colspan=1>N</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Surrendered</td><td rowspan=1 colspan=1>N</td><td rowspan=1 colspan=1>Card returned to CIA and no longerneeded</td></tr><tr><td rowspan=1 colspan=1>Lost</td><td rowspan=1 colspan=1>Y</td><td rowspan=1 colspan=1>Lost card declaration</td></tr><tr><td rowspan=1 colspan=1>Stolen</td><td rowspan=1 colspan=1>Y</td><td rowspan=1 colspan=1>Stolen card declaration</td></tr><tr><td rowspan=1 colspan=1>Malfunctioning</td><td rowspan=1 colspan=1>Y</td><td rowspan=1 colspan=1>Defective card declaration</td></tr><tr><td rowspan=1 colspan=1>Expired</td><td rowspan=1 colspan=1>N</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Replaced</td><td rowspan=1 colspan=1>N</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>Renewed</td><td rowspan=1 colspan=1>N</td><td rowspan=1 colspan=1></td></tr><tr><td rowspan=1 colspan=1>InExchange</td><td rowspan=1 colspan=1>Y</td><td rowspan=1 colspan=1>Exchange of a card (start)</td></tr><tr><td rowspan=1 colspan=1>Exchanged</td><td rowspan=1 colspan=1>Y</td><td rowspan=1 colspan=1>exchange of a card (end)</td></tr></table>

The card status values in red ('Y' in 2nd column) will be defined as the only values allowed as new card status values in the TCN "ModCardStatus" transaction (XML message). TCN will not check the validity of the state transition declared in this transaction (e.g. it will not prevent declaring a card 'Exchanged' while its current status was 'Stolen' as TCN doesn't know the current card status). It's up the MS responsibility to check the validity of such state transition (and return a ModStatusCode=CardStatusInvalid in the XML response message).

## Table 1 – New card status

Basic flow

The basic flow consists of the following steps:

<table><tr><td rowspan=1 colspan=1>Step</td><td rowspan=1 colspan=1>Action</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>TACHOnet deciphers the received request and logs the received requestas-is in its tracking database.</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>TACHOnet validates its syntax and assigns it a TACHOnet refid(TCNRefId).</td></tr></table>

Continued on next page

# Use Case 03 – Declaration of card status modification, Continued

Basic flow (continued)

<table><tr><td rowspan=1 colspan=1>Step</td><td rowspan=1 colspan=1>Action</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>TACHOnet will build as many new requests as issuing Member Statecodes identified in the original request. TACHOnet figures out the targetissuing Member States based on the CIA country code given in theoriginal request. Every new request only contains card number(s) issuedby a particular Member State.</td></tr><tr><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>For each identified issuing Member State(s), TACHOnet builds, logs andencrypts the new request, sends it to the Member State and waits forreceiving the response.</td></tr><tr><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>For each received response, TACHOnet deciphers it, logs it as-is in itstracking database and validates its syntax. If it&#x27;s valid, TACHOnet storesthe response message (linked to the TCNRefId) in the database (for laterbuilding the single consolidated response that TACHOnet will send whenall responses are received or when the timeout is reached).</td></tr><tr><td rowspan=1 colspan=1>6</td><td rowspan=1 colspan=1>When all responses are received or when the timeout is reached,TACHOnet builds, logs and encrypts the consolidated response (from theresponses received so far), and sends it to the original caller.</td></tr></table>

The same alternate flows as described for UC-01 (page 23) may exist depending on the result of some events/actions of the basic flow.

## Special requirements

• Non-repudiation of transaction must be guaranteed

• Data privacy must also be guaranteed

• All Member State CIAs must provide services (using proposed messages formats below and proposed technical rules in [2]) for:

• Sending a request for declaring card status modification to TACHOnet

• Receiving and handling a TACHOnet request for declaring card status modification

• Sending TACHOnet a response to such TACHOnet request (asynchronous)

• Receiving and handling a TACHOnet response to original request for declaring card status modification (asynchronous)

## Pre-conditions

• The CIA sending the declaration must be defined in TACHOnet

• The CIA sending the declaration must send its request using the TACHOnet required request format (see below)

• The CIA sending the declaration must have first sent a request for checking the card number for which status modification is required.

## Use Case 03 – Declaration of card status modification, Continued

## Post-conditions

• The CIA sending the declaration has received a response to its request.

• The CIA having issued the card has received the request and processed it.

## Actors

• A CIA declaring the card status modification (CIA’s clerk or enforcer)

• The CIA having issued the card

• The TACHOnet system

## Messages flow diagram

The following diagram outlines the flow of messages exchanged between actors (assuming a single card number is specified in the original request, meaning TACHOnet has to forward the request to the Member State having issued the card):

![](images/b75d90bda12c52a7a7a16fa70bb9334eccfb32d428c9982beb319e93d1e4d7ce.jpg)  
Figure 7 – UC-03 messages flow

<table><tr><td></td><td></td></tr><tr><td>XML Messages Please refer to [2] for a complete description</td><td></td></tr><tr><td>Additional remarks</td><td>• In case of problems (e.g. network problem,...) when sending a message (request, response), TACHOnet will automatically retry to send it 3 times at regular interval till request timeout.</td></tr></table>

# Use Case 03 – Declaration of card status modification, Continued

## Use Case 04 – Send Card/Driving License Assignment

## Description

This use case is born from the “Luxemburg agreement” (see [3] for more details). It should be used by CIAs in the particular case when a card has been issued to a driver who showed a foreign driving license. The CIA must then warn, via TACHOnet, the Member State having issued the driving license that a brand new card has been issued with the corresponding driving license number. Upon receipt of such request, the Member State having issued the driving license should store that information (issued card number associated to the driving license number) in its own local data store.

## Basic flow

The basic flow consists of the following steps:

<table><tr><td rowspan=1 colspan=1>Step</td><td rowspan=1 colspan=1>Action</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>TACHOnet deciphers the received request and logs the received requestas-is in its tracking database.</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>TACHOnet validates its syntax and assigns it a TACHOnet refid(TCNRefId).</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>TACHOnet will build as many new requests as issuing Member Statecodes identified in the original request (e.g. if more than one card/drivinglicense number is given in the request). TACHOnet figures out the issuingMember State code(s) based on the driving license issuing nation (and notthe card issuing Member State code) given for each sub request. Everynew request only contains card and driving license number(s) issued by aparticular Member State.</td></tr><tr><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>For each identified issuing Member State(s), TACHOnet builds, logs andencrypts the new request, sends it to the Member State and waits forreceiving the response.</td></tr><tr><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>For each received response, TACHOnet deciphers it, logs it as-is in itstracking database and validates its syntax. If it&#x27;s valid, TACHOnet storesthe response message (linked to the TCNRefId) in the database (for laterbuilding the single consolidated response that TACHOnet will send whenall responses are received or when the timeout is reached).</td></tr><tr><td rowspan=1 colspan=1>6</td><td rowspan=1 colspan=1>When all responses are received or when the timeout is reached,TACHOnet builds, logs and encrypts the consolidated response (from theresponses received so far), and sends it to the original caller.</td></tr></table>

The same alternate flows as described for UC-01 (page 23) may exist depending on the result of some events/actions of the basic flow.

# Use Case 04 – Send Card/Driving License Assignment, Continued

## Special

• Non-repudiation of transaction must be guaranteed

## requirements

• Data privacy must also be guaranteed

• All Member State CIAs must provide services (using proposed messages formats below and proposed technical rules in [2]) for:

• Sending a request for checking a card number to TACHOnet

• Receiving and handling a TACHOnet request for checking a card number

• Sending TACHOnet a response to such TACHOnet request (asynchronous)

• Receiving and handling a TACHOnet response to original request (asynchronous)

## Pre-conditions

• The CIA sending the request must be defined in TACHOnet

• The CIA sending the request must send it using the TACHOnet required request format (see below)

## Post-conditions

• The CIA sending the request has received a receipt and a response to its request.

## Actors

• A CIA requesting the update

• All CIAs to which TACHOnet will broadcast the request

• The TACHOnet system

## XML Messages

Please refer to [2] for a complete description.

Continued on next page

# Use Case 04 – Send Card/Driving License Assignment, Continued

The following diagram outlines the flow of messages exchanged between actors (assuming a single card number is specified in the original request, meaning TACHOnet has to forward the request to the Member State having issued the card):

![](images/26148ac3acdb460a55ef21dabb1b9c286043ba78ba74e51e0936455683629876.jpg)  
Figure 8 – UC-04 messages flow

• In case of problems (e.g. network problem,...) when sending a message (request, response), TACHOnet will automatically retry to send 3 times it at regular interval till request timeout.

## Use Case 05 – Get Phonex Search Keys

## Description

This use case consists of getting from TACHOnet the computed search keys (based on the Phonex algorithm) corresponding to the given last name and first names.

The Member State CIAs should call upon this service when issuing a new card to get the computed search keys of the driver’s surname and first names, so to store them in their local data store. When a Member State CIA will receive a TACHOnet request for checking driver’s issued card, it should use the search keys given in the request to search against their local data store (along with the given driver’s birth date). It’s therefore of major importance to use a common algorithm and to store computed search keys in the local data store.

Nevertheless, Member States are free to use their own Phonetic algorithm (if existing like in Germany). In such a case, it’s the Member State responsibility to compute the search keys based on the given driver’s surname and first of the first names.

## Basic flow

The basic flow consists of the following steps:

<table><tr><td rowspan=1 colspan=1>Step</td><td rowspan=1 colspan=1>Action</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>The CIA calls the TACHOnet service giving the driver&#x27;s surname andfirst names.</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>TACHOnet checks the input parameters and, if valid, computes thecorresponding surname and first of the first names search keys.</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>TACHOnet returns the computed search keys as output parameters.</td></tr></table>

## Alternate flows

2a If the input parameters are invalid (e.g. illegal character,…), TACHOnet returns a negative status code to the request.

## Special requirements

• This service should ideally be implemented as a synchronous Web Service.

• A web interface on top of this service should also be supplied to allow the CIA users to access manually these TACHOnet services.

• A downloadable version of this web service should also be made available (.NET and Java) to enable some Member States to install and use it locally.

## Pre-conditions

The caller must provide the mandatory input parameters.

## Post-conditions

The caller has received the computed search keys (or a negative error code).

## Actors

• A CIA (when issuing a new card) or an enforcer (via a CIA)

• The TACHOnet system

Continued on next page

## Use Case 05 – Get Phonex Search Keys, Continued

The following diagram outlines the flow of messages exchanged between actors:

![](images/867104736187d30b0e6bea29de431414843a78555908bfaf26f5ebc634130ec0.jpg)  
Figure 9 – UC-05 messages flow

## Input data

• Surname (sSN): driver’s surname

• First names (sFN): driver’s first names

## Output data

• Surname (sKSN): computed search key of driver’s surname

• First names (sKFN): computed search key of driver’s first of first names

## Additional remarks

• Parameters should be UTF-8 encoded.

• These services are opened to anyone connected on TESTA (no special security).

## Open issues

## Use Case 06 – Get US/Ascii Transliteration

## Description

This use case consists of getting from TACHOnet the US/Ascii (ISO 646 IRV) transliteration (From Latin or Greek) of the given driver’s surname, first names, place of birth and driving license number.

Up to now, this use case only provides the transliteration from Greek (according to the ISO 843:1997 standard) or Latin to US/Ascii. Other transliterations (e.g. Cyrillic to US/Ascii according to ISO 9:1995) will be provided when needed.

## Basic flow

The basic flow consists of the following steps:

<table><tr><td rowspan=1 colspan=1>Step</td><td rowspan=1 colspan=1>Action</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>The CIA calls the TACHOnet service giving the driver&#x27;s surname, firstnames, place of birth and driving license number.</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>TACHOnet checks the input parameters and, if valid, transliterates thecorresponding values into US/Ascii.</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>TACHOnet returns the transliterated values as output parameters.</td></tr></table>

## Alternate flows

2a If the input parameters are invalid (e.g. illegal character,…), TACHOnet returns a negative status code to the request.

## Special requirements

• This service should ideally be implemented as a synchronous Web Service.

• A web interface on top of this service should also be supplied to allow the CIA users to access manually these TACHOnet services.

• A downloadable version of this web service should also be made available (.NET and Java) to enable some Member States to install and use it locally.

## Pre-conditions

The caller must provide the mandatory input parameters.

## Post-conditions

The caller has received the computed search keys (or a negative error code).

## Actors

• A CIA (when issuing a new card) or an enforcer (via a CIA)

• The TACHOnet system

Continued on next page

![](images/c0cf0d1a8433a91a071e6eba027d3cf3030315f6d78b74bdb5ae98b44e466afa.jpg)  
Figure 10 – UC-06 messages flow

## Use Case 06 – Get US/Ascii Transliteration, Continued

The following diagram outlines the flow of messages exchanged between actors:

## Input data

• Surname (SN): driver’s surname

• First names (FN): driver’s first names

• Place of Birth (PB): driver’s place of birth

• Driving license number (DLN): driver’s driving license number

## Output data

The transliterated values as an array of strings

## Additional remarks

• Parameters should be UTF-8 encoded.

• These services are opened to anyone connected on TESTA (no special security).

## Open issues

# Section 2.2 - Use Case Package “TCN Statistics Tasks” Overview

Introduction This section describes the use cases related to the “TCN Statistics Tasks” package. The following diagram lists the use cases of this package:

![](images/b8c1ee2e9aedf23fefef276c72a9ff51d8b0cf167a72296f00ad7d70f4fb4884.jpg)  
Figure 11 –Use Case Package “TCN Statistics Tasks”

<table><tr><td rowspan=1 colspan=1>Topic</td><td rowspan=1 colspan=1>See Page</td></tr><tr><td rowspan=1 colspan=1>Use Case 07 – “Add a new CIA&quot;</td><td rowspan=1 colspan=1>40</td></tr><tr><td rowspan=1 colspan=1>Use Case 08 – “Reset Password&quot;</td><td rowspan=1 colspan=1>42</td></tr><tr><td rowspan=1 colspan=1>Use Case 09 – “Generate Statistics&quot;</td><td rowspan=1 colspan=1>44</td></tr><tr><td rowspan=1 colspan=1>Use Case 10 – “Browse Statistics&quot;</td><td rowspan=1 colspan=1>47</td></tr><tr><td rowspan=1 colspan=1>Use Case 11 – Log the message</td><td rowspan=1 colspan=1>52</td></tr></table>

## Use Case 07 – “Add a new CIA”

<table><tr><td>Brief Description</td><td colspan="2">In order to get access to the Statistics Reporting part of the TACHOnet system, every Member State will be assigned a CIA Administrator&#x27;s account (and password). This use case enables the TCN Administrator to create a new CIA Administrator account in the Active Directory for a CIA Administrator using the Microsoft Management Console Active Directory Users and Computers</td></tr><tr><td>Primary Actor</td><td colspan="2">(MMC). • TCN Administrator (or delegates to the operator).</td></tr><tr><td>Preconditions</td><td colspan="2">The actor has access to the Microsoft Management Console Active Directory Users and Computers.</td></tr><tr><td>Postconditions</td><td colspan="2">The new CIA Administrator has been created and has now access to the ReportManager Web site.</td></tr><tr><td>Stakeholders and Interest</td><td colspan="2">Access to the ReportManager Web site (providing the TCN usage statistics reports) should only be allowed to the CIA Administrators. Therefore, every CIA Administrator must be assigned a user account and password.</td></tr><tr><td>Sequence Diagram</td><td colspan="2"></td></tr><tr><td colspan="2"></td><td colspan="2"></td></tr><tr><td></td><td colspan="2"></td></tr><tr><td colspan="3"></td></tr></table>

Continued on next page

## Use Case 07 – “Add a new CIA”, Continued

## Basic Flow

<table><tr><td>Step</td><td>Action</td></tr><tr><td>1</td><td>A new Member State is added to the TACHOnet configuration (see Use- Case 13 – “Manage Member State&quot; at page 55). The TCN Administrator (or operator) creates the new CIA Administrator account (and password) usingtheMicrosoft Management Console Active Directory Users and Computers.</td></tr></table>

## Alernative Flow

## Technology and Data Variations List

\- Access to the ReportManager web site will be secured by using Windows accounts.

## Assumptions

The TCN Administrator has access to the Microsoft Management Console Active Directory Users and Computers. In the production environment (if not, he may ask the operator to perform the steps).

\- Only one CIA Administrator account will be created per Member State.

\- All users are managed in the Active Directory.

\- The TACHOnet Administrator will also be assigned one account.

## Open issues

## Use Case 08 – “Reset Password”

<table><tr><td>Brief Description</td><td colspan="2">This use case enables the TCN Administrator to reset in the Active Directory the password of a CIA Administrator using the Microsoft Management Console Active Directory Users and Computers (MMC).</td></tr><tr><td></td><td colspan="2">Primary Actor TCN Administrator (or delegates to the operator).</td></tr><tr><td>Preconditions</td><td colspan="2">The actor has access to the Microsoft Management Console Active Directory Users and Computers and the CIA Administrator&#x27;s account has already been created.</td></tr><tr><td></td><td colspan="2">Postconditions The CIA Administrator&#x27;s password has been reset.</td></tr><tr><td>Stakeholders and Interest</td><td colspan="2">A CIA Administrator might forget her password. Therefore, the TCN Administrator should be able to reset it.</td></tr><tr><td>Sequence Diagram</td><td colspan="2"></td></tr><tr><td rowspan="2"></td><td colspan="2"></td></tr><tr><td><img src="images/590be365c64c0ef917c3fd657389e4365b71e1b27e40ec5acdec0cfcbd139d20.jpg"/></td><td rowspan="2"></td></tr><tr><td></td><td></td></tr></table>

Continued on next page

## Use Case 08 – “Reset Password”, Continued

## Basic Flow

<table><tr><td rowspan=1 colspan=1>Step</td><td rowspan=1 colspan=1>Action</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>The CIA Administrator warns (via email) the TCN Administrator thatshe forgots her password.</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>The TCN Administrator (or operator) resets the corresponding CIAAdministrator account&#x27;s password using the MicrosoftManagement Console Active Directory Users andComputers.</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>The TCN Administrator warns the CIA Administrator (via email) to logon again and change her password.</td></tr></table>

## Alernative Flow

## Technology and Data Variations List

Access to the ReportManager web site will be secured by using Windows accounts.

## Assumptions

The TCN Administrator has access to the Microsoft Management Console Active Directory Users and Computers. In the production environment (if not, he may ask the operator to perform the steps).

\- Only one CIA Administrator account will be created per Member State.

\- All users are managed in the Active Directory.

\- The TACHOnet Administrator will also be assigned one account.

## Open issues

## Use Case 09 – “Generate Statistics”

This use case consists of transferring (at regular interval – nightly basis) all expired TACHOnet transactions (completed or after timeout), storing them and generating some usage statistics for the TCN Administrator and every CIA Administrators.

The usage statistics should give information about the incoming requests (from a CIA to TACHOnet) for a given period:

\- The list of requests for the last 14 days (List).

The percentage of each status code values (Timeout, ServerError,…) for each CIA (Consolidated chart).

The count and percentage of each status code values for each CIA (Consolidated list).

The count and percentage of each CIA for each type of requests (Consolidated list).

The count and percentage of each type of requests (CheckIssuedCards, CheckCardStatus,…) for each mode – Batch and On-line - (Consolidated list).

The usage statistics should give information about the outgoing requests (from TACHOnet to a CIA) for a given period:

\- The list of requests for the last 14 days (List).

\- The percentage of OK status code value for each CIA (Consolidated chart).

The percentage of each status code values (Timeout, ServerError,…) for each CIA (Consolidated chart).

The count and percentage of each status code values for each CIA (Consolidated list).

The count and percentage of each CIA for each type of requests (Consolidated list).

The count and percentage of each type of requests for each mode – Batch and On-line - (Consolidated list).

The consolidated lists should also give information about the minimum, maximum and average value of the time it took to complete the transaction and for the given timeout value.

<table><tr><td>Primary Actor TCN Reporting System.</td><td></td></tr><tr><td></td><td>PreconditionsExpired transactions are available and the Agent is scheduled on a nightly base.</td></tr><tr><td></td><td>Continued on next page</td></tr></table>

## Use Case 09 – “Generate Statistics”, Continued

Postconditions Transactions are transferred and statistics are generated.

Stakeholders Statistics are a major measurement tool for identifying potential problems, assessing and Interests the overall usage of the system.

## Sequence Diagram

![](images/3f62e2bad91df2aa41a4cdbc4e6a77baccd62a9201ef0553915b1394d4bb1220.jpg)

Basic Flow The basic flow for this use case is the following.

<table><tr><td rowspan=1 colspan=1>Step</td><td rowspan=1 colspan=1>Action</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>The Agent executes the Job: Tachonet Transfer based on its schedule.</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>The Job: Tachonet Transfer executes the SP: TransferInfo whichtransfers expired transactions from the production database to thedatawarehouse database.</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>The Job: Tachonet Transfer executes the SP: ProcessInfo.</td></tr><tr><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>The SP: ProcessInfo executes the Dts: TachonetDWOlap Processingwhich processes cubes in the OLAP database.</td></tr></table>

## Alernative Flow

## Use Case 09 – “Generate Statistics”, Continued

## Special Requirements

There are two special requirements.

<table><tr><td rowspan=1 colspan=1>RequirementId</td><td rowspan=1 colspan=1>Description</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Usage statistics should be made available as a web-basedinterface.</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>The web-based interface should support download of therendered statistics in different formats as xml and Excel.</td></tr></table>

## Technology and Data Variations List

SQL Reporting Services (brand new service of SQL Server 2000) will be used to provide the whole TCN reporting solution (user interface, report generation, report design,…).

## Assumptions

Open issues

## Use Case 10 – “Browse Statistics”

## Brief Description

This use case consists of allowing the TCN Administrator and every CIA Administrator to browse, via a secure Web interface, the usage statistics reports.

There are five reports available:

\- Requests from MS – List for the list of requests for the last 14 days (List).

Requests from MS – Consolidation for the percentage of each status code value for each CIA (Consolidated chart), the count and percentage of each status code value for each CIA (Consolidated list), the count and percentage of each CIA for each type of requests (Consolidated list) and the count and percentage of each type of requests for each mode – Batch and On-line - (Consolidated list).

\- Requests to MS – List for the list of requests for the last 14 days (List).

Requests to MS – Top for the percentage of OK status code value for each CIA (Consolidated chart).

Requests to MS – Consolidation for the percentage of each status code value for each CIA (Consolidated chart), the count and percentage of each status code value for each CIA (Consolidated list), the count and percentage of each CIA for each type of requests (Consolidated list) and the count and percentage of each type of requests for each mode – Batch and On-line - (Consolidated list).

## Primary Actor

\- TCN Administrator.

CIA Administrator.

## Preconditions

\- Transactions are transferred and statistics are generated.

\- The actor has access to the ReportManager Web site.

## Postconditions

The actor has browsed and downloaded report(s).

## Stakeholders and Interests

Statistics are a major measurement tool for identifying potential problems, assessing the overall usage of the system.

## Use Case 10 – “Browse Statistics”, Continued

Sequence Diagram

![](images/0a52eeb14d2f30e77b024f03c237a3928506992d776381646bea2060068f98e2.jpg)

Basic Flow

The basic flow for this use case is the following.

<table><tr><td rowspan=1 colspan=1>Step</td><td rowspan=1 colspan=1>Action</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>The actor logs in the system using the standard basic security mechanismof the web browser.</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>If the login succeeded, the actor browses the reports on theReportManager Web site.</td></tr><tr><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>If it is the first access of the actor, he may change his password on theUsers Web site.</td></tr></table>

Continued on next page

## Use Case 10 – “Browse Statistics”, Continued

Alernative Flow Some alternatives are described below, referred to in the basic flow.

<table><tr><td>Step</td><td>Action</td></tr><tr><td>2b</td><td>If the login failed, the actor calls the TCN Administrator to reset his password or to do the adequate operation.</td></tr></table>

## Requests from MS - List

User: EUROPE\pfrancis

<table><tr><td colspan="7">Count 663</td></tr><tr><td>Mode</td><td>Name</td><td>From</td><td>Status</td><td>Start At</td><td>End At</td><td>Timeout</td></tr><tr><td>Batch</td><td>CheckCardStatus</td><td>TCN_A</td><td>OK</td><td>4/02/2004 14:22:51</td><td>4/02/2004 14:22:53</td><td>172800</td></tr><tr><td>Batch</td><td>CheckCardStatus</td><td>TCN_A</td><td>OK</td><td>4/02/2004 14:23:51</td><td>4/02/2004 14:23:53</td><td>172800</td></tr><tr><td>Batch</td><td>CheckCardStatus</td><td>TCN_A</td><td>OK</td><td>4/02/2004 14:24:51</td><td>4/02/2004 14:24:53</td><td>172800</td></tr><tr><td>Batch</td><td>CheckCardStatus</td><td>TCN_A</td><td>OK</td><td>4/02/2004 14:25:50</td><td>4/02/2004 14:25:51</td><td>172800</td></tr><tr><td>Batch</td><td>CheckCardStatus</td><td>TCN_A</td><td>OK</td><td>4/02/2004 14:26:50</td><td>4/02/2004 14:26:51</td><td>172800</td></tr></table>

Requests from MS - Consolidation
<table><tr><td colspan="10">User : EUROPE\pfrancis</td></tr><tr><td>Mode</td><td>Name</td><td>From</td><td>Status</td><td>Count</td><td>Percent</td><td>Intervale MIN</td><td>Intervale MAX Intervale AVG</td><td></td><td>Timeout MIN</td></tr><tr><td>田All</td><td></td><td></td><td></td><td>663</td><td>100,00 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr><tr><td>日Batch</td><td></td><td></td><td></td><td>663</td><td>100,00 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr><tr><td>田All</td><td></td><td></td><td></td><td>663</td><td>100,00 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr><tr><td rowspan="5"></td><td>CheckCardStatus</td><td></td><td></td><td>663</td><td>100,00 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr><tr><td></td><td>田All</td><td></td><td>663</td><td>100,00 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr><tr><td></td><td>TCN_A</td><td></td><td>663</td><td>100,00 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr><tr><td></td><td>All</td><td></td><td>663</td><td>100,00 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr><tr><td></td><td>OK</td><td></td><td>663</td><td>100,00 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr></table>

## Requests to MS - List

User : EUROPE\pfrancis

<table><tr><td colspan="7">Count 11267</td></tr><tr><td>Mode</td><td>Name</td><td>To</td><td>Status</td><td>Start At</td><td>End At</td><td>Timeout</td></tr><tr><td>Batch</td><td>CheckCardStatus</td><td>TCN_B</td><td>OK</td><td>4/02/2004 14:22:51</td><td>4/02/2004 14:22:53</td><td>172800</td></tr><tr><td>Batch</td><td>CheckCardStatus</td><td>TCN_D</td><td>OK</td><td>4/02/2004 14:22:51</td><td>4/02/2004 14:22:53</td><td>172800</td></tr><tr><td>Batch</td><td>CheckCardStatus</td><td>TCN_DK</td><td>OK</td><td>4/02/2004 14:22:51</td><td>4/02/2004 14:22:53</td><td>172800</td></tr><tr><td>Batch</td><td>CheckCardStatus</td><td>TCN_E</td><td>OK</td><td>4/02/2004 14:22:51</td><td>4/02/2004 14:22:53</td><td>172800</td></tr><tr><td>Batch</td><td>CheckCardStatus</td><td>TCN_F</td><td>OK</td><td>4/02/2004 14:22:51</td><td>4/02/2004 14:22:53</td><td>172800</td></tr></table>

Continued on next page

# Use Case 10 – “Browse Statistics”, Continued

## Requests to MS - Top

![](images/026fcff78075d38b1201d5a88a9dc83327239346e8130c0f367079d5059f4d13.jpg)

## Requests to MS - Consolidation

<table><tr><td colspan="3">LOrOr LpiiamcTs</td><td rowspan="2"></td><td colspan="4"></td><td rowspan="2">Timeout MIN</td></tr><tr><td>Mode Name</td><td>To</td><td>Status</td><td>Count</td><td>Percent</td><td>Intervale MIN Intervale MAX</td><td>Intervale AVG</td></tr><tr><td>田All</td><td colspan="2"></td><td>11.267</td><td>100,00 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr><tr><td>日Batch</td><td colspan="2"></td><td>11.267</td><td>100,00 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr><tr><td colspan="3">田All</td><td>11.267</td><td>100,00 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr><tr><td rowspan="6"> CheckCardStatus</td><td></td><td></td><td>11.267</td><td>100,00 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr><tr><td>田All</td><td></td><td>11.267</td><td>100,00 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr><tr><td>TCN_B</td><td></td><td>663</td><td>5,88 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr><tr><td></td><td>All</td><td>663</td><td>5,88 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr><tr><td>OK</td><td></td><td>663</td><td>100,00 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr><tr><td>TCN_D</td><td></td><td>663</td><td>5,88 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr><tr><td></td><td>田TCN_DK</td><td></td><td>663</td><td>5,88 %</td><td>1</td><td>2</td><td>1</td><td>172.800</td></tr></table>

## Special Requirements

There is one special requirement.

<table><tr><td>Requirement Id</td><td>Description</td></tr><tr><td>1</td><td>The generated reports should be dynamic reports.</td></tr></table>

SQL Reporting Services (brand new service of SQL Server 2000) will be used to provide the whole TCN reporting solution (user interface, report generation, report design,…).

## Assumptions

\- A special web site (single page) will also be built to allow the CIA Administrator to change her account’s password.

\- Only one CIA Administrator account will be created per Member State.

\- All users are managed in the Active Directory.

\- The TACHOnet Administrator will also be assigned one account.

# Use Case 10 – “Browse Statistics”, Continued

Open issues

## Use Case 11 – Log the message

## Description

This use case consists of logging as-is every message sent or received by TACHOnet.

Such logging is provided out-of-the-box by BizTalk and will be configured at the channel level using the BizTalk Messaging Manager tool.

## Basic flow

The basic flow consists of the following steps:

<table><tr><td rowspan=1 colspan=1>Step</td><td rowspan=1 colspan=1>Action</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Upon receiving a message, TACHOnet should log it as-is in the trackingdatabase.</td></tr><tr><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Prior to sending a message, TACHOnet should log it as-is in the trackingdatabase.</td></tr></table>

## Alternate flows

• TACHOnet should also provide a system for archiving (e.g. removing from the tracking database to flat files) “old” messages (how long should TACHOnet keep track of a message?).

## Special requirements

• Great care must be taken when setting up the tracking database in terms of sizing (the number of the messages to be logged might quickly become huge), performance (the logging mechanism should not impede overall TACHOnet system performance), availability (high availability must be guaranteed through clustering,...) and security (restricted administrative access, strong backup policies,...).

## Pre-conditions

• A message (request, response) is received by TACHOnet or about to be sent by TACHOnet.

## Post-conditions

• The received/sent message is logged in the tracking database

## Actors

• TACHOnet system

## Additional remarks

Open issues - How long should TACHOnet keep track of a message?

## Section 2.3 - Use Case Package “TCN System Tasks” Overview

This section describes the use cases related to the “TCN Monitoring” package. The following diagram lists the use cases of this package:

![](images/58ba81b2b76b3b7873f020bc57625508007fe6a81cff942c438ca3875a670647.jpg)  
Figure 12 –Use Case Package “TCN System Tasks”

This section contains the following topics:

<table><tr><td rowspan=1 colspan=1>Topic</td><td rowspan=1 colspan=1>See Page</td></tr><tr><td rowspan=1 colspan=1>Use-Case 12 – “Monitor the $\scriptstyle \mathbf { S y s t e m } ^ { \prime \prime }$ </td><td rowspan=1 colspan=1>54</td></tr><tr><td rowspan=1 colspan=1>Use-Case 13 – &quot;Manage Member $\mathrm { S t a t e } ^ { \prime \prime }$ </td><td rowspan=1 colspan=1>55</td></tr></table>

## Use-Case 12 – “Monitor the system”

<table><tr><td>Brief Description</td><td>This use case consists of monitoring the whole TACHOnet system. Such monitoring will be based on the MOM (Microsoft Operations Manager)</td></tr><tr><td></td><td>product, used as standard monitoring tool by the EC DI&#x27;s Data Center. Managing BizTalk through MOM is made possible by installing the BizTalk Management Pack for MOM. Nevertheless, as this pack consists of more than 700 rules, some configuration need to be made (in close collaboration with EC DI&#x27;s Data Center people) to configure the set of rules required for monitoring the BizTalk</td></tr><tr><td></td><td>configuration of TACHOnet.</td></tr><tr><td>Primary Actor</td><td>TCN Administrator</td></tr><tr><td>Preconditions</td><td>The TCN Administrator has access to the MOM console. The TCN Administrator has managed alerts sent through the MOM console.</td></tr><tr><td>Postconditions Stakeholders</td><td>In order to constantly keep the availability and performance of the TACHOnet system at an optimum level, the system must constantly monitored and should raise</td></tr><tr><td>and Interests</td><td>some events when particular problems (HW, SW,...) occur.</td></tr><tr><td>Basic Flow</td><td>See MOM documentation. Technology and</td></tr><tr><td>Data Variations List</td><td></td></tr><tr><td>Assumptions</td><td>MOM is used as central monitoring system.</td></tr><tr><td>Open issues</td><td>Will the TACHOnet servers be directly monitored from the central MOM console or should TACHOnet provide ?</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>Is there any special FW configuration between the TACHOnet servers and the</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>central MOM console?</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td>What are the BizTalk rules that need be configured in MOM and how?</td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr><tr><td></td><td></td></tr></table>

## Use-Case 13 – “Manage Member State”

<table><tr><td>Brief Description</td><td colspan="2">This use case consists of managing a Member State CIA in terms of TACHOnet configuration (add, edit, remove a Member State CIA).</td></tr><tr><td>Primary Actor</td><td colspan="2">TCN Administrator</td></tr><tr><td>Preconditions</td><td colspan="2">The TCN Administrator has access to the BizTalk Messaging Manager and BizTalk Server Administrationtools</td></tr><tr><td>Postconditions</td><td colspan="2">The Member State CIA configuration in TACHOnet has been updated.</td></tr><tr><td>Stakeholders and Interests</td><td colspan="2">All Member States will not be ready at production day 1. Moreover, new candidate Member States will potentially join TACHOnet in the near future. The configuration of existing Member States could also change. Therefore, it&#x27;s important to provide the TCN Administrator with the tools or procedures to manage the TACHOnet configuration of a Member State.</td></tr><tr><td>Basic Flow</td><td colspan="2">Managing Member States consists of adding a new Member State or modifying the current configuration of a Member State (url address, digital certificates,...) or</td></tr><tr><td rowspan="6">outlined below:</td><td colspan="2">removing a Member State (?). All these manual tasks will be described in details in the “TCN Operational Guide&quot; document. Anyway, some of these major tasks are</td></tr><tr><td colspan="2">Adding a new Member State: The following table lists the activities to carry out to add a new Member State in the</td></tr><tr><td colspan="2">TACHOnet configuration:</td></tr><tr><td colspan="2">BizTalk configuration: Create the BizTalk organization corresponding to the new Member State</td></tr><tr><td colspan="2" rowspan="2">(“TCN_&lt;count rycode&gt;&quot;) with its relevant properties.</td></tr><tr><td>Create the corresponding BizTalk messaging ports. Create the corresponding BizTalk distribution list (“A11–</td></tr><tr><td colspan="2">&lt;countrycode&gt;&quot;).</td></tr><tr><td colspan="2"></td></tr><tr><td colspan="2">Update all the other BizTalk distribution lists to add the new messaging port (send request) corresponding to the new Member State.</td></tr><tr><td colspan="2">Create the corresponding BizTalk channels. Create the corresponding BizTalk receive functions (in test environment).</td></tr><tr><td colspan="2">Reporting System:</td></tr></table>

\- Add a new CIA Administrator account

## Use-Case 13 – “Manage Member State”, Continued

## Basic Flow (continued)

## Modifying the current configuration of a Member State:

Changing the phone/fax/email of the Member State:

\- Update the custom properties of the BizTalk organization corresponding to the Member State

\- Changing the url address where TACHOnet should send XML messages:

\- Update the transport type of the BizTalk messaging port corresponding to the Member State.

## Technology and Data Variations List

BizTalk Server 2002 provides the necessary tools to manage its configuration.   
These will be leveraged to update the Member States configuration.

## Assumptions

The TCN Administrator is a BizTalk Administrator and has access to the BizTalk Messaging Manager and BizTalk Server Administration tools (or will delegate to the effective BizTalk Administrator).

## Open issues