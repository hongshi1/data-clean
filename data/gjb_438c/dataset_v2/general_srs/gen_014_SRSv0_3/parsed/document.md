# Software Requirements Specification (SRS) for the <Nodes Portal Toolkit (NPT)>

Technical Report · September 2011

CITATIONS 0

READS 23,506

2 authors, including:

![](images/0d965c544f8fea7bb7a09b9343e19e08dcd640ba881159905cb30b47201e4150.jpg)

Bruno Danis

Université Libre de Bruxelles

184 PUBLICATIONS   2,677 CITATIONS

SEE PROFILE

Some of the authors of this publication are also working on these related projects:

![](images/df44f0149b7ad4cbd12e66bbcbc50bc55b7b4a6df11e9b02c53fb380788aaeb8.jpg)

Biogeographic Atlas of the Southern Ocean View project

rECTO - Refugia and Ecosystem Tolerance in the Southern Ocean View project

# Software Requirements Specification (SRS) For the <Nodes Portal Toolkit (NPT)>

Version 0.3

![](images/fdc69e9a58af82c1d812c193ab0f3b9320e34fe0da5ad3d19a9ced8d966fb8cd.jpg)

September 2011

## Revision History

<table><tr><td>Contributors</td><td>Date</td><td>Reason for changes</td></tr><tr><td>B. Danis, S. Renaudier B. Chi-Jen Ko, B. Danis, D. Remsen, F. Pando, M. A. Mora, N. Noé, P. Desmet, S. Renaudier,</td><td>18 Jul 2011 13 Sep 2011</td><td>Initial draft, open for discussion Second version, includes comments and revisions from the NPT-Advisory Group and GBIF-Secretariat</td></tr><tr><td>W. Addink A. Heughebaert, B. Chi-Jen Ko, B. Danis, D. Remsen, M. Carausu, N. Noé, N. Youdjou, P. Desmet, S. Renaudier, S. Rycroft, V.</td><td>27 Sep 2011</td><td>Third version, includes revisions from the NPT-Technical Task Force, circulated to NPT-Advisory Group and GBIF-Secretariat</td></tr></table>

Revision	  History 2   
Introduction 6   
Purpose 6   
Scope	  of	  the	  NPT 6   
Product	  perspective	  and	  historical	  background 7   
Document	  conventions 7   
Actor	  Survey 9   
Primary	  actors 9   
Front	  end	  users 9   
Back	  office	  users 9   
Secondary	  actors 9   
Use-­‐Case	  Model	  Survey 11   
Back	  end	  users 11   
Administrator 11   
Data	  manager 12   
Portal	  manager 15   
Front	  end	  users 16   
Visitor 16   
Registered	  visitor 19   
Functional	  requirements 21   
Back	  end	  functionalities 21   
Administrator 21   
Data	  manager 21   
Portal	  manager 23   
Front-­‐end	  functionalities 24   
Visitor 24   
Registered	  visitor 25   
Nonfunctional	  Requirements 26   
Assumptions	  and	  Dependencies 26   
Security	  Requirements 26   
Scalability	  Requirements 26   
Robustness	  Requirements 27   
Interoperability	  Requirements 27   
Operating	  Environment 27   
Usability	  Requirements 27   
Supportability	  Requirements 27   
User	  Documentation	  Requirements 27   
Design	  and	  Implementation	  Constraints 28   
Interfaces 28   
User	  Interfaces 28   
Pagination 28   
Distribution	  map 28   
Filter	  building	  interface 28   
Hardware	  Interfaces 28   
Software	  Interfaces 28   
Application	  programming	  interface 28   
GBIF	  IPT 29   
GBIF	  resource	  Web	  services 29   
GBIF	  Registry 29   
Communications	  Interfaces 29   
Licensing	  Requirements 29   
Glossary 30   
Appendixes 32   
Back	  end	  use	  cases 32   
Administrator 32   
Data	  manager 36   
Portal	  manager 43   
Front	  end	  use	  cases 46   
Visitor 46   
Registered	  visitor 52   
Business	  rules 54   
References 55   
Table	  of	  figures   
Figure	  1:	  Primary	  Actors. .9   
Figure	  2:	  Secondary	  Actors .... .10   
Figure	  3:	  Administrator	  Use	  Cases... .11   
Figure	  4:	  Data	  Manager	  Use	  Cases	  -­‐ Data	  source	  and	  harvesting	  job	  management.... .12   
Figure	  5:	  Data	  manager	  Use	  Cases	  -­‐ Resource	  Registration .13   
Figure	  6:	  Data	  manager	  Use	  Cases	  -­‐ Resource	  Management.. .15   
Figure	  7:	  Portal	  Manager	  Use	  Cases ... .16   
Figure	  8:	  Visitor	  Use	  Cases	  –	  	  selecting	  and	  viewing	  occurrence	  records. .17   
Figure	  9:	  Visitor	  Use	  Cases	  (continued) .. .18   
Figure	  10:	  Registered	  Visitor	  Use	  Cases. .19

## Introduction

The NPT is a community, open source project.

## Purpose

The present Nodes Portal Toolkit (NPT) Software Requirements Specification (SRS) document was prepared as the next incremental step after the NPT Scoping and Requirements (S&R) document, which was drafted by the NPT Advisory Group (AG), during the Madrid workshop in March 2011 and publicly released in June 2011.

The purpose of the SRS is to describe the software requirements for the NPT, reaching a level of detail which makes it fit to be circulated amongst the NPT stakeholders, and in particular amongst the NPT developers. It is also intended to serve as a basis for discussion during the Brussels NPT technical meeting (September 2011), during which elements for a high-level architectural and design document will be gathered.

The purpose of the current version of the SRS document is to clarify, validate and verify the requirements for the NPT as expressed by the NPT-AG, focusing on its functional aspects. The SRS captures and describes the desired behavior of the end product in a wide range of situations.

Some of the non-functional requirements in this document were taken as is from the scoping document and can still be refined.

The present document is also intended to be a planning instrument for the development of the NPT and its potential derivatives.

## Scope of the NPT

As described in the NPT (S&R) document, the Nodes Portal Toolkit is a tool to facilitate discovery and access to GBIF data at a national, regional or thematic level, including the possibility to offer access to additional sources of information. The primary users of the NPT are the Node Managers (specifically, the technical teams involved in GBIF Participant Nodes and/or relevant biodiversity information networks), as well as the End-Users of the data published through the various NPT instances. The NPT should enable the Node Managers to customize the way GBIF-compliant data are served to their own community or to a specific group of data users.

Development of the NPT is based on the needs expressed by the Nodes community. To the best extent possible, the wishes of the Nodes and their communities regarding NPT functionalities will be expressed in the flexibility and scalability of the tool itself. Commitment and feedback is expected from the Nodes community in order to align their needs and the functionalities of the NPT, as it evolves in its various releases.

Even if the NPT is intended to be a technical tool, NPT-based portals are also envisioned as an important public relations and communication tool for GBIF Participant Nodes, serving also to demonstrate the possibilities that the GBIF network offers at different levels (national, regional, thematic).

## Product perspective and historical background

The need for GBIF Participant Node data portals distinct from (and interacting with) the GBIF central portal was already recognized at the first meeting of the Nodes committee in Oct 2002 in San Juan, Costa Rica as a major component of the overall GBIF architecture. This quickly led to the release of a first version of a GBIF Portal toolkit for Nodes (Dec 2002). As there were still no GBIF-mediated data to share at that time, this early portal was mainly a communication tool (featuring a hierarchical directory of links, files and html pages, announcements, news and articles, calendar of events, news channels syndication, etc.…). It also featured a repository for biodiversity data files exported from databases (prefiguring to some degree the approach adopted by the current IPT software in which exported Darwin Core Archives are used to facilitate indexing). Nodes started to deploy the GBIF DiGIR network to publish species occurrence data in the fall of 2004 (BioCASE sites following shortly after). A first prototype GBIF central portal was officially launched in February 2004. In April 2004, Nodes recommended to consider the development of a data portal toolkit for nodes as part of a work program. In October 2004, the recommendation became a ranked priority, second only to hiring a full time Nodes officer. Between May and October 2005, a draft requirements document was developed, a workshop was held in Copenhagen and some resources were allocated to an early prototype presented in April 2006 in South Africa. At that time, the customized portal for nodes was pretty much perceived as a national or thematic subset of the central portal. Subsequently the secretariat focused on the development of a new central portal and the prototype custom portal for nodes was never deployed. In the summer of 2009, an online survey was conducted with preliminary results presented at the Nodes meeting in Copenhagen in October. This led to convening an Advisory Group (AG) in December 2009 in Montreal to work on a scoping document for a Nodes Portal Toolkit (NPT) and a set of recommendations on how to develop, implement and deploy such a toolkit. The AG met again in March 2011 in Madrid and prepared the scoping (S&R) document, under the supervision of the NPT Coordinator. After revision and consultation loops between the NPT AG, the GBIF secretariat and the NPT-Coordinator, the S&R document was publicly released in June 2011.

## Document conventions

The main type of convention used throughout this document helps to represent the level of priority of the different software requirements. These priorities are established in function of many factors, including those identified in the NPT (S&R) document, consultation loops with the NPT stakeholders, and technical constraints which represent the reality at the moment this document is prepared.

In the functional requirements section, to keep consistency with the NPT (S&R) document, the same color codes define priorities as defined by the MoSCoW method.

<table><tr><td>Green: NPT V1.0 must have this feature</td></tr><tr><td>Yellow: NPT V1.0 should have this feature if at all possible</td></tr><tr><td>Red: NPT V1.0 could have this feature (if it doesn&#x27;t affect anything else)</td></tr><tr><td>Black: NPT V1.0 won&#x27;t have this feature (maybe in the future)</td></tr></table>

In Use Case surveys, and Use Case sections, priorities and frequency are attributed an increasing index, ranging from 1 (low priority/frequency) to 5 (high priority/frequency).

In the nonfunctional requirements section, a series of acronyms are used, as described below:

BR = Business Rules

CO = Design and Implementation Constraints

CR = Capacity Requirements

IR = Interoperability Requirements

OE = Operating Environment

RR = Robustness Requirements

ScaR = Scalability Requirements

SR = Security Requirements

SupR = Supportability Requirements

UD = User Documentation

UR = Usability Requirements

## Actor Survey

This section lists the different actors NPT instances shall interact with: end users (primary actors) and actors from which the system needs assistance to satisfy a goal (secondary actors).

Primary actors

![](images/83e64ebe03c786d4fb066a64661d1b91dd97a0fa2b916133adeb0fd89313db89.jpg)  
Figure	  1:	  Primary	  Actors

Front	  end	  users

1. Visitors: the data consumers, they only have access to the system frontend.

2. Registered visitors: once registered, a visitor is offered extra functionalities to save and load custom occurrence filters.

## Back	  office	  users

1. Administrators: they are responsible for installing, configuring and monitoring the system and managing modules. They are also in charge of managing user accounts and associated roles. Administrators should have skills in system administration, database management and deployment of Web applications. They should also have basic knowledge of Web-based GIS.

2. Data managers: they are in charge of maintaining portal resources. Data managers should have basic knowledge of taxonomy and biodiversity data.

3. Portal managers: they configure the portal according to the node profile and contribute news, blog entries and articles.

Secondary actors

![](images/542a7dc4b7d9eda7bd82695701df3c0a8a1602c53e17557e10daa9f4ea22f347.jpg)  
Figure	  2:	  Secondary	  Actors

1. GBIF Registry: the GBIF Registry is an application that manages the nodes, organizations, resources, and IPT installations registered with GBIF, making them discoverable and interoperable. More importantly in the context of the NPT, it also acts as a repository for extensions.

2. Data sources: resource repositories that NPT instances can harvest. Two types of sources are envisioned in a first approach: IPT instances and GBIF portal Web services (using GBIF Portal API). Other data source types may be provided as modules in the future.

## Use-Case Model Survey

Back end users

Administrator
<table><tr><td>UC ID</td><td>Name</td><td>Priority</td></tr><tr><td>UC-A1</td><td>Manage modules</td><td></td></tr><tr><td>UC-A2</td><td>Configure the distribution map</td><td></td></tr><tr><td>UC-A3</td><td>Manage spatial layers</td><td></td></tr><tr><td>UC-A4</td><td>Manage user accounts</td><td></td></tr></table>

![](images/42c5a7654c378ed82347b17b8ae725f1c648d616cd383efdd0051f0c0cfee1e2.jpg)  
Figure	  3:	  Administrator	  Use	  Cases

Manage	  modules
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-A1 - Manage modules</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The administrator selects to manage modules in order to add newfunctionalities to the system by installing modules. This use cases alsoallows the administrator to configure or update previously installedmodules.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Administrator</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr></table>

Configure the	  distribution	  map
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-A2 - Configure the distribution map</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The administrator selects to configure the distribution map to set thespecific projection and default extent for the Node area of interest.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Administrator</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>1</td></tr></table>

Manage	  spatial	  layers
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-A3 - Manage spatial layers</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The administrator selects to add or delete the spatial layers displayed on thedistribution map for the specific Node.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Administrator</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>3</td></tr></table>

Manage	  user	  accounts
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-A4 - Manage user accounts</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The security officer performs this use case in order to create or deleteaccounts for the portal staff members so they can access restrictedfunctionalities.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Administrator</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>4</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>3</td></tr></table>

Data	  manager  
![](images/5860d1d3601e66740a384edad22064538b7406eeddfaf67fd75a73b6c9f71dca.jpg)  
Figure	  4:	  Data	  Manager	  Use	  Cases -­‐  
Data	  source	  and	  harvesting	  job	  management

<table><tr><td>UC ID</td><td>Name</td><td>Priority</td></tr><tr><td>UC-DM1</td><td>Manage resources</td><td></td></tr><tr><td>UC-DM2</td><td>Register a new data source</td><td></td></tr><tr><td>UC-DM3</td><td>Register a GBIF index data source</td><td></td></tr><tr><td>UC-DM4</td><td>Register an IPT data source</td><td></td></tr><tr><td>UC-DM5</td><td>Unregister a data source</td><td></td></tr><tr><td>UC-DM6</td><td>Manage harvesting jobs</td><td></td></tr><tr><td>UC-DM7</td><td>Check core resources consistency with registered data sources</td><td></td></tr><tr><td>UC-DM8</td><td>Trigger a harvesting job</td><td></td></tr><tr><td>UC-DM9</td><td>Update taxonomic backbone</td><td></td></tr><tr><td>UC-DM10</td><td>Install an extension</td><td></td></tr></table>

Manage	  resources
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-DM1 - Manage resources</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The data manager wants to manage resources in order to import a newresource, edit a resource metadata or delete a resource.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Data manager</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>3</td></tr></table>

![](images/555787ae293453eda487f87ad318775a3579b968b84d4bff5c47ee7050d4ac58.jpg)  
Figure	  5:	  Data	  manager	  Use	  Cases -­‐ Resource	  Registration

Register	  a	  new	  data	  source
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-DM2 - Register a new data source</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The data manager registers a new data source so the associated coreresource is harvested during next harvesting job.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Data manager - Secondary: Data source</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr></table>

Register	  a	  GBIF	  index	  data	  source
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-DM3 - Register a GBIF index data source</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>Specializes Register a new data source to allow specific configuration forGBIF occurrence Web services data sources.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Data manager - Secondary: GBIF Web services</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr></table>

Register	  an	  IPT	  data	  source
<table><tr><td>Identifier-Name</td><td colspan="3">UC-DM4 - Register an IPT data source</td></tr><tr><td>Description</td><td colspan="3">Specializes Register a new data source to allow specific configuration for IPT</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="3" rowspan="1">data sources.</td></tr><tr><td colspan="1" rowspan="1">Actors</td><td colspan="3" rowspan="1">Data manager - Secondary: IPT instance</td></tr><tr><td colspan="1" rowspan="1">Priority</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">Frequency</td><td colspan="1" rowspan="1">2</td></tr></table>

Unregister	  a	  data	  source
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-DM5 - Unregister a data source</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The data manager previously added a data source which is no more relevantto the node or which is no more available. The data manager wants tounregister this source.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Data manager</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr></table>

Manage	  harvesting	  jobs
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-DM6 - Manage harvesting jobs</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The data manager wants to manage jobs so as to monitor finished andupcoming jobs, schedule a new job or cancel a scheduled job.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Data manager</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>1</td></tr></table>

Check	  core	  resources	  consistency	  with	  registered	  data	  sources

<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-DM7 - Check core resources consistency with registered data sources</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The data manager checks core resources consistency with registered datasources to identify outdated core resources and unavailable data sources.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Data manager - Secondary: Registered occurrence data source</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>3</td></tr></table>

Trigger	  a	  harvesting	  job
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-DM8 - Trigger a harvesting job</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The data manager selects to backup portal data so as to synchronize theportal biodiversity data with those hosted on the registered data sources.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Primary: Data manager - Secondary: Data source</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>3</td></tr></table>

![](images/588bad72ad13d12f93d0842cce116554b2ee0d054119ddfd7b96a840cf26a4b8.jpg)  
Figure	  6:	  Data	  manager	  Use	  Cases -­‐ Resource	  Management

Update	  taxonomic	  backbone
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-DM9- Update taxonomic backbone</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The data manager updates the taxonomic backbone.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Data manager</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>3</td></tr></table>

Install	  an	  extension
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-DM10 - Install an extension</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The data manager wants to install an extension to allow the system to dealwith extra attributes for records of core resources.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Primary: Data manager - Secondary: GBIF registry</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>3</td></tr></table>

Portal	  manager  
![](images/2a66d369ff8612c0b39653b96885198cdf08e1b6024ed968ae2a59efc11189be.jpg)

Figure	  7:	  Portal	  Manager	  Use	  Cases
<table><tr><td>UC ID</td><td>Name</td><td>Priority</td></tr><tr><td>UC-PM1</td><td>Configure data metrics visibility</td><td></td></tr><tr><td>UC-PM3</td><td>Customize NPT instance</td><td></td></tr><tr><td>UC-PM3</td><td>Configure front office languages</td><td></td></tr></table>

Configure	  data	  metrics	  visibility
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-PM3 - Configure data metrics visibility</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The portal manager configures data metrics visibility in order to hide somemetrics from the visitors in the front office.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Portal manager</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>1</td></tr></table>

Customize	  NPT	  instance
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-PM2 - Customize NPT instance</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>Portal manager customizes NPT instance to adapt the portal appearanceand parameters to fit its organization.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Portal manager</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>1</td></tr></table>

## Configure	  front	  office	  languages

<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-PM3 - Configure front office languages</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The data manager selects to manage front office languages so as to set thedefault language and chooses alternate language.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Portal manager</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr></table>

## Front end users

Visitor

<table><tr><td>UC ID</td><td>Name</td><td>Priority</td></tr><tr><td>UC-V1</td><td>Send feedback to the portal contact person</td><td></td></tr><tr><td>UC-V2</td><td>Select occurrence records and view distribution map</td><td></td></tr><tr><td>UC-V3</td><td>View occurrence record selection as a table</td><td></td></tr><tr><td>UC-V4</td><td>Export occurrence record selection</td><td></td></tr><tr><td>UC-V5</td><td>Export distribution map as an image</td><td></td></tr><tr><td>UC-V6</td><td>Search portal using full text search</td><td></td></tr><tr><td>UC-V7</td><td>Contact an occurrence resource publisher</td><td></td></tr><tr><td>UC-V8</td><td>Export a checklist</td><td></td></tr><tr><td>UC-V9</td><td>Choose portal language</td><td></td></tr></table>

![](images/40f6c20badc6d2e7a8d34e75cfde9280d3facd1543f546b9ab5794bf6c77a040.jpg)  
Figure	  8:	  Visitor Use	  Cases –  
selecting	  and	  viewing	  occurrence	  records

Send	  feedback	  to	  the	  portal	  contact	  person
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-V1 - Send feedback to the portal contact person</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The visitor sends feedback to the portal contact person so as tocommunicate remarks or suggestions about the portal or about the hosteddata.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>1</td></tr></table>

Select	  occurrence	  records	  and	  view	  distribution	  map
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-V2 - Select occurrence records and view distribution map</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The visitor wants to discover and access occurrence records. He can selecthis records of interest using simple taxonomic search or a more elaborateadvanced search by combining various criteria.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>5</td></tr></table>

View	  occurrence	  record	  selection	  as	  a	  table
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=1>UC-V3 - View occurrence record selection as a table</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=1>User selects to view occurrence records selection as a table in order todisplay their attributes.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=1>Visitor</td></tr></table>

<table><tr><td>Priority</td><td>3</td><td>Frequency</td><td>3</td></tr><tr><td></td><td></td><td></td><td></td></tr></table>

Export	  occurrence	  record	  selection
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-V4 - Export occurrence record selection</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>User exports the occurrence selection for further analysis.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>4</td></tr></table>

Export	  distribution	  map	  as	  an	  image
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-V5 - Export distribution map as an image</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The visitor exports distribution map as an image so as to be able to insert itin a document.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>4</td></tr></table>

![](images/698b181498fdcbb8e658388ff35b3521ad9d4124492a0d96a9db025558f10b71.jpg)  
Figure	  9:	  Visitor	  Use	  Cases	  (continued)

Search	  portal	  using	  full	  text	  search
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-V6 - Search portal using full text search</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The visitor searches resource metadata, blog, article and news entries usingfull text search in order to find and access matching resources and entries.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>4</td></tr></table>

Contact	  an	  occurrence	  resource	  publisher
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-V7 - Contact an occurrence resource publisher</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The visitor contacts the publisher of an occurrence resource to requestmore information or send a comment.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>1</td></tr></table>

Export	  	  a	  checklist
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-V8 - Export a checklist</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The visitor downloads a checklist for consultation/analysis.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr></table>

Choose	  portal	  language
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-V9 - Choose portal language</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The visitor chooses his language of preference.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr><tr><td rowspan=1 colspan=1>Preconditions</td><td rowspan=1 colspan=3>The portal manager has configured front office languages with at least onealternate language.</td></tr></table>

Registered	  visitor
<table><tr><td>UC ID Name</td><td></td><td>Priority</td></tr><tr><td>UC-RV1</td><td>Save a custom filter</td><td></td></tr><tr><td>UC-RV2</td><td>Load a custom filter</td><td></td></tr><tr><td>UC-RV3</td><td>Delete a custom filter</td><td></td></tr></table>

![](images/0570b09a41b88315a09f43ae1c8e8d4f769daf7de5f6408ad550736c3e4ad26c.jpg)  
Figure	  10:	  Registered	  Visitor Use	  Cases

Save	  a custom	  filter
<table><tr><td></td><td colspan="3">Identifier-Name UC-RV1 - Save a custom filter</td></tr><tr><td colspan="1" rowspan="1">Description</td><td colspan="3" rowspan="1">The registered visitor has built a filter and wants to be able to reuse it inthe future. He saves the filter in his profile.</td></tr><tr><td colspan="1" rowspan="1">Actors</td><td colspan="3" rowspan="1">Registered visitor</td></tr><tr><td colspan="1" rowspan="1">Priority</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">Frequency</td><td colspan="1" rowspan="1">2</td></tr></table>

## Load	  a	  custom	  filter

<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-RV2 - Load a custom filter</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>Visitor loads a filter he previously saved in his profile.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Registered visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr></table>

Delete	  a	  custom	  filter

<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-RV3 - Delete a custom filter</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>Visitor has built a filter. He wants to be able to reuse it in future visits. Hesaves the filter to be able to load it later.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Registered visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr></table>

## Functional requirements

## Back end functionalities

Administrator
<table><tr><td>FR ID</td><td>Name</td><td>UC ID</td><td>Priority</td></tr><tr><td>FR-A1</td><td>The system shall allow the administrator to install modules</td><td>UC-A1</td><td></td></tr><tr><td>FR-A2</td><td>The system shall allow the administrator to uninstall modules</td><td>UC-A1</td><td></td></tr><tr><td>FR-A3</td><td>The system shall allow the administrator to configure the distribution map projection</td><td>UC-A2</td><td></td></tr><tr><td>FR-A4</td><td>The system shall allow the administrator to configure the distribution map default extent</td><td>UC-A2</td><td></td></tr><tr><td>FR-A5</td><td>The system shall allow the administrator to edit the email server configuration (URL, port, account)</td><td></td><td></td></tr><tr><td>FR-A6</td><td>The system shall allow the administrator to add a spatial layer to the distribution map</td><td>UC-A3</td><td></td></tr><tr><td>FR-A7</td><td>The system shall allow the administrator to remove a spatial layer from the distribution map</td><td>UC-A3</td><td></td></tr><tr><td>FR-A8</td><td>The system shall allow the administrator to edit the name of a spatial layer of the distribution map</td><td>UC-A3</td><td></td></tr><tr><td>FR-A9</td><td>The system shall allow the administrator to view error logs</td><td></td><td></td></tr><tr><td>FR-A10</td><td>The system shall allow the administrator to download error logs</td><td></td><td></td></tr><tr><td>FR-A11</td><td>The system shall allow the security officer to create a new user account</td><td>UC-A4</td><td></td></tr><tr><td>FR-A12</td><td>The system shall allow the security officer to delete a user account</td><td>UC-A4</td><td></td></tr><tr><td>FR-A13</td><td>The system shall allow the security officer to assign a role to a user account</td><td>UC-A4</td><td></td></tr><tr><td>FR-A14</td><td>The system shall allow the security officer to remove a role from a user account</td><td>UC-A4</td><td></td></tr><tr><td>FR-A15</td><td>The system shall allow the security officer to edit the email address associated with a user account</td><td>UC-A4</td><td></td></tr><tr><td>FR-A16</td><td>The system shall allow the security officer to view audit logs</td><td></td><td></td></tr><tr><td>FR-A17</td><td>The system shall allow the security officer to download audit log entries for a given month</td><td></td><td></td></tr></table>

Data	  manager

<table><tr><td>FR ID</td><td>Name</td><td>UC ID</td><td>Priority</td></tr><tr><td>FR-DM1</td><td>The system shall allow the data manager to import an occurrence resource</td><td>UC-DM1</td><td></td></tr><tr><td>FR-DM2</td><td>The system shall allow the data manager to delete an occurrence resource</td><td>UC-DM1</td><td></td></tr><tr><td>FR-DM3</td><td>The system shall allow the data manager to edit the metadata of an occurrence resource</td><td>UC-DM1</td><td></td></tr><tr><td>FR-DM4</td><td>The system shall allow the data manager to search occurrence resources by keywords</td><td>UC-DM1</td><td></td></tr><tr><td>FR-DM5</td><td>The system shall allow the data manager to import a</td><td>UC-DM1</td><td></td></tr></table>

<table><tr><td>checklist resource</td><td colspan="2"></td></tr><tr><td>FR-DM6</td><td>The system shall allow the data manager to delete a checklist resource</td><td>UC-DM1</td></tr><tr><td>FR-DM7</td><td>The system shall allow the data manager to edit the metadata of a checklist resource</td><td>UC-DM1</td></tr><tr><td>FR-DM8</td><td>The system shall allow the data manager to search checklist resources by keywords</td><td>UC-DM1</td></tr><tr><td>FR-DM9</td><td>The system shall allow the data manager to import a multimedia resource</td><td>UC-DM1</td></tr><tr><td>FR-DM10</td><td>The system shall allow the data manager to delete a multimedia resource</td><td>UC-DM1</td></tr><tr><td>FR-DM11</td><td>The system shall allow the data manager to edit the metadata of a multimedia resource</td><td>UC-DM1</td></tr><tr><td>FR-DM12</td><td>The system shall allow the data manager to search multimedia resources by keywords</td><td>UC-DM1</td></tr><tr><td>FR-DM13</td><td>The system shall allow the data manager to import a bibliographic resource</td><td>UC-DM1</td></tr><tr><td>FR-DM14</td><td>The system shall allow the data manager to delete a bibliographic resource</td><td>UC-DM1</td></tr><tr><td>FR-DM15</td><td>The system shall allow the data manager to edit the metadata of a bibliographic resource The system shall allow the data manager to search</td><td>UC-DM1 UC-DM1</td></tr><tr><td>FR-DM16 FR-DM17</td><td>bibliographic resources by keywords The system shall allow the data manager to import an</td><td>UC-DM1</td></tr><tr><td>FR-DM18</td><td>institution resource The system shall allow the data manager to delete an</td><td>UC-DM1</td></tr><tr><td>FR-DM19</td><td>institution resource The system shall allow the data manager to edit the</td><td>UC-DM1</td></tr><tr><td>FR-DM20</td><td>metadata of an institution resource The system shall allow the data manager to search</td><td>UC-DM1</td></tr><tr><td>FR-DM21</td><td>institution resources by keywords The system shall allow the data manager to import an</td><td>UC-DM1</td></tr><tr><td>FR-DM22</td><td>expert resource The system shall allow the data manager to delete an</td><td>UC-DM1</td></tr><tr><td>FR-DM23</td><td>expert resource The system shall allow the data manager to edit the</td><td>UC-DM1</td></tr><tr><td>FR-DM24</td><td>metadata of an expert The system shall allow the data manager to search expert</td><td>UC-DM1</td></tr><tr><td>FR-DM25</td><td>resources by keywords The system shall allow the data manager to register a</td><td>UC-DM3</td></tr><tr><td>FR-DM26</td><td>GBIF index data source The system shall allow the data manager to register an</td><td>UC-DM4</td></tr><tr><td>FR- DM27</td><td>IPT data source The system shall allow the data manager to unregister an IPT data source</td><td>UC-DM5</td></tr><tr><td>FR- DM28</td><td>The system shall allow the data manager to unregister a</td><td>UC-DM5</td></tr><tr><td>FR- DM29</td><td>GBIF index data source Schedule a harvesting job</td><td>UC-DM6</td></tr><tr><td>FR- DM30</td><td>Cancel an harvesting job</td><td>UC-DM6</td></tr><tr><td>FR- DM31</td><td>View report for a harvesting jobs</td><td>UC-DM6</td></tr><tr><td>FR- DM32</td><td>Check core resources consistency with registered data</td><td>UC-DM7</td></tr><tr><td>FR- DM33</td><td>sources</td><td>UC-DM8</td></tr><tr><td>FR- DM34</td><td>Trigger a harvesting job The system shall allow the data manager to request</td><td></td></tr><tr><td colspan="2">restoration of the latest backup</td><td rowspan="3"></td></tr><tr><td>FR- DM35</td><td>Update taxonomic backbone UC-DM9</td></tr><tr><td>FR- DM36 Install an extension</td><td>UC-DM10</td></tr><tr><td>FR- DM37 Monitor portal usage</td><td></td></tr></table>

Portal	  manager
<table><tr><td>FR ID</td><td>Name</td><td>UC ID</td><td>Priority</td></tr><tr><td>FR-PM1</td><td>The system shall allow the portal manager to configure data metrics visibility</td><td>UC-PM1</td><td></td></tr><tr><td>FR-PM2</td><td>The system shall allow the portal manager to change the logo displayed on the portal</td><td>UC-PM2</td><td></td></tr><tr><td>FR-PM3</td><td>The system shall allow the portal manager to change the Node name displayed on the portal</td><td>UC-PM2</td><td></td></tr><tr><td>FR-PM4</td><td>The system shall allow the portal manager to change the portal banner</td><td>UC-PM2</td><td></td></tr><tr><td>FR-PM5</td><td>The system shall allow the portal manager to configure the name and email of the portal contact person</td><td>UC-PM2</td><td></td></tr><tr><td>FR-PM6</td><td>The system shall allow the portal manager to configure the Network summary information</td><td>UC-PM2</td><td></td></tr><tr><td>FR-PM7</td><td>The system shall allow the portal manager to choose the default language of the portal</td><td></td><td></td></tr><tr><td>FR-PM8</td><td>The system shall allow the portal manager to add an alternate language to the portal</td><td></td><td></td></tr><tr><td>FR-PM9</td><td>The system shall allow the portal manager to remove an alternate language to the portal</td><td></td><td></td></tr><tr><td>FR-PM10</td><td>The system shall allow the portal manager to contribute a portal news entry</td><td></td><td></td></tr><tr><td>FR-PM11</td><td>The system shall allow the portal manager to edit a portal news entry</td><td></td><td></td></tr><tr><td>FR-PM12</td><td>The system shall allow the portal manager to delete a portal news entry</td><td></td><td></td></tr><tr><td>FR-PM13</td><td>The system shall allow the portal manager to contribute a blog post</td><td></td><td></td></tr><tr><td>FR-PM14 FR-PM15</td><td>The system shall allow the portal manager to edit a blog post The system shall allow the portal manager to delete a blog</td><td></td><td></td></tr><tr><td></td><td>post</td><td></td><td></td></tr><tr><td>FR-PM16</td><td>The system shall allow the portal manager to manage the portal menu</td><td></td><td></td></tr><tr><td>FR-PM17</td><td>The system shall allow the portal manager to add a page to the portal</td><td></td><td></td></tr><tr><td>FR-PM18</td><td>The system shall allow the portal manager to delete a page from the portal</td><td></td><td></td></tr><tr><td>FR-PM19</td><td>The system shall allow the portal manager to edit a page from the portal</td><td></td><td></td></tr><tr><td>FR-PM20</td><td>The system shall allow the portal manager to edit the HTML metadata tags for the portal pages to help the portal to be discoverable through search engines</td><td></td><td></td></tr></table>

## Front-end functionalities

Visitor

<table><tr><td>FR ID</td><td>Name</td><td>UC ID</td><td>Priority</td></tr><tr><td>FR-V1</td><td>The system shall allow a visitor to build an occurrence selection filter</td><td>UC-V1</td><td></td></tr><tr><td>FR-V2</td><td>The system shall allow a visitor to add a taxonomic criterion to a filter</td><td>UC-V1</td><td></td></tr><tr><td>FR-V3</td><td>The system shall allow a visitor to add a dataset criterion to a filter</td><td>UC-V1</td><td></td></tr><tr><td>FR-V4</td><td>The system shall allow a visitor to add a depth criterion to a filter</td><td>UC-V1</td><td></td></tr><tr><td>FR-V5</td><td>The system shall allow a visitor to add an altitude criterion to a filter</td><td>UC-V1</td><td></td></tr><tr><td>FR-V6</td><td>The system shall allow a visitor to add a basis of records criterion to a filter</td><td>UC-V1</td><td></td></tr><tr><td>FR-V7</td><td>The system shall allow a visitor to add a geographic criterion to a filter</td><td>UC-V1</td><td></td></tr><tr><td>FR-V8</td><td>The system shall allow a visitor to add a date criterion to a filter</td><td>UC-V1</td><td></td></tr><tr><td>FR-V9</td><td>The system shall allow a visitor to remove a criterion from a filter</td><td>UC-V1</td><td></td></tr><tr><td>FR-V10</td><td>The system shall allow a visitor to select occurrence records using a filter</td><td>UC-V2</td><td></td></tr><tr><td>FR-V11</td><td>The system shall allow a visitor to view the distribution map for an occurrence record selection</td><td>UC-V2</td><td></td></tr><tr><td>FR-V12</td><td>The system shall allow a visitor to view an occurrence record selection as a table</td><td>UC-V3</td><td></td></tr><tr><td>FR-V13</td><td>The system shall allow a visitor to export an occurrence record selection</td><td>UC-V4</td><td></td></tr><tr><td>FR-V14</td><td>The system shall allow a visitor to export the distribution map for an occurrence record selection as an image</td><td>UC-V5</td><td></td></tr><tr><td>FR-V15</td><td>The system shall allow a visitor to search all the portal content using full text search</td><td>UC-V6</td><td></td></tr><tr><td>FR-V16</td><td>The system shall allow a visitor to contact an occurrence resource publisher</td><td>UC-V7</td><td></td></tr><tr><td>FR-V17</td><td>The system shall allow a visitor to export a checklist The system shall allow a visitor to choose his preferred</td><td>UC-V8</td><td></td></tr><tr><td>FR-V18</td><td>language for the portal interface</td><td>UC-V9</td><td></td></tr><tr><td>FR-V19</td><td>The system shall allow a visitor to send feedback to the portal contact person</td><td>UC-V10</td><td></td></tr><tr><td>FR-V20</td><td>The system shall allow a visitor to view latest blog posts</td><td></td><td></td></tr><tr><td>FR-V21</td><td>The system shall allow a visitor to read a blog post</td><td></td><td></td></tr><tr><td>FR-V22</td><td>The system shall allow a visitor to view latest portal news entries</td><td></td><td></td></tr><tr><td>FR-V23</td><td>The system shall allow a visitor to read a portal news entry</td><td></td><td></td></tr><tr><td>FR-V24</td><td>The system shall allow a visitor to view details for a taxon</td><td></td><td></td></tr><tr><td>FR-V25</td><td>The system shall allow a visitor to view metadata for a dataset</td><td></td><td></td></tr><tr><td>FR-V26</td><td>The system shall allow a visitor to view metadata for a checklist</td><td></td><td></td></tr><tr><td>FR-V27</td><td>The system shall allow a visitor to view details for a</td><td></td><td></td></tr></table>

<table><tr><td>bibliographic record</td><td></td><td></td></tr><tr><td>FR-V28</td><td>The system shall allow a visitor to view details for an institution</td><td></td></tr><tr><td>FR-V29</td><td>The system shall allow a visitor to view details for an expert</td><td></td></tr><tr><td>FR-V30</td><td>The system shall allow a visitor to view metadata for a multimedia file</td><td></td></tr><tr><td>FR-V31</td><td>The system shall allow a visitor to download a multimedia file</td><td></td></tr><tr><td>FR-V32</td><td>The system shall allow a visitor to navigate (pan, zoom in and out) a distribution map</td><td></td></tr><tr><td>FR-V33</td><td>The system shall allow a visitor to toggle spatial layers visible/hidden on a distribution map</td><td></td></tr><tr><td>FR-V34</td><td>The system shall allow a visitor to register</td><td></td></tr><tr><td>FR-V35</td><td>The system shall allow a visitor to access the log in functionality</td><td></td></tr><tr><td>FR-V36</td><td>The system shall allow a visitor to request to be sent his password by email</td><td></td></tr><tr><td>FR-V37</td><td>The system shall allow a visitor to share a distribution map on twitter</td><td></td></tr><tr><td>FR-V38</td><td>The system shall allow a visitor to access a dashboard displaying data metrics for the portal</td><td></td></tr><tr><td>FR-V39</td><td>The system shall allow a visitor to export data metric archives for the portal</td><td></td></tr><tr><td>FR-V40</td><td>The system shall allow a visitor to view Network summary information</td><td></td></tr><tr><td>FR-V41</td><td>The system shall allow a visitor to view information about tools and services offered by the portal</td><td></td></tr><tr><td>FR-V42</td><td>The system shall allow a visitor to view latest news from GBIF newsfeeds relayed by the system</td><td></td></tr></table>

Registered	  visitor
<table><tr><td>FR ID</td><td>Name</td><td>UC ID</td><td>Priority</td></tr><tr><td>FR-RV1</td><td>The system shall allow a registered visitor to save a custom filter</td><td>UC-RV1</td><td></td></tr><tr><td>FR-RV2</td><td>The system shall allow a registered visitor to load a custom filter</td><td>UC-RV2</td><td></td></tr><tr><td>FR-RV3</td><td>The system shall allow a registered visitor to delete a custom filter</td><td>UC-RV3</td><td></td></tr></table>

## Nonfunctional Requirements

## Assumptions and Dependencies

DE1 The operation of the system depends on GBIF registry to allow addition of new extensions.

DE2 The operation of the system depends on GBIF occurrence Web services<sup>1</sup> to harvest a data source if it is of GBIF global index type.

DE3 The operation of the system to harvest occurrence resource for an IPT instance data source depends on that IPT instance.

## Security Requirements

SR1 The system shall retain an audit log for all successful back end operations.

SR2 The system shall restrict access to all functionalities altering data to data managers (BR4).

SR3 The system shall restrict access to user management functionalities to administrators. (BR3).

SR4 The system shall restrict access to module management functionalities to administrators (BR6).

SR5 The system shall restrict access to distribution map configuration functionalities to administrators (BR6).

SR6 The system shall restrict access to portal manager for the following functionalities: manage blog posts, pages and news entries, customize NPT instance and choose languages available on the front end (BR5).

SR7 The system shall restrict access to portal manager for blog management functionalities (BR5).

SR8 The system shall restrict access to portal manager for news management functionalities (BR5).

SR9 The system shall restrict access to portal manager for the NPT instance customization function (BR5).

SR10 The system shall restrict access to portal manager for front-end available language management functionalities (BR5).

## Scalability Requirements

ScaR1 The system should be able to cope with 300 000 000 occurrence records (size of the GBIF index at the time of writing).

ScaR2 The system shall have no limitation on the number records the export occurrence records functionality can process (UC-V4, FR-V13).

ScaR3 The system should be able to cope (without crashing) with a wide range of stress situations.

ScaR4 The system should perform reasonably under important workload (queries and data discovery).

## Robustness Requirements

RR1 An error tracking system shall be in place.

RR2 Database transactions shall insure data consistency in case of failure.

RR3 Backups of all system data shall be generated on a weekly basis.

RR4 Upon request from the data manager, a backup shall be restored within the next 24 hours.

## Interoperability Requirements

IR1 The system shall allow importing checklist resources as DwC-A files.

IR2 The system shall allow importing occurrence resources as DwC-A files.

IR3 The system shall allow exporting checklist resources as DwC-A files.

IR4 The system shall allow exporting occurrence records as DwC-A files.

IR5 The system shall allow exporting occurrences records as KMZ files.

IR6 The system shall allow exporting occurrences records as CSV files.

IR7 The system shall allow exporting occurrences records as ESRI shapefiles.

IR8 The system shall allow exporting distribution map as images.

IR9 The system shall allow exporting core resource metadata as EML profiles.

IR10 The system shall allow using the Audubon Core format for multimedia metadata.

## Operating Environment

OE1 The system shall operate with the two latest major releases of the following Web browsers: Firefox, Opera, Chrome, Internet Explorer and Safari.

OE2 The system shall operate on a server running Linux, Windows server or Mac OS.

## Usability Requirements

UR1 The interface for end-users should be relatively intuitive and easy to use,

without requiring extensive technical assistance, support or off line user guides.

UR2 For system managers, guides may be needed to explore advanced functionalities, but those advanced functionalities should be as intuitive as possible.

UR3 Maintenance in terms of user interface configuration, user rights management, and data source settings should be done with visual tools.

UR4 The system shall allow a visitor to select the language used on the front end.

UR5 The system shall display friendly error messages to the users.

## Supportability Requirements

SupR1 A clear and standard practice for the maintenance and documentation of code should be set in place, agreed and communicated as a best practice. Any features developed outside the core of the NPT should follow that practice.

## User Documentation Requirements

UD1 The system shall provide a short tutorial video explaining how to search and export occurrence records.

UD2 One offline installation guide with step-by-step instructions shall be provided (with different notes for each OS the system can operate on).

UD3 A wiki, organized around the different types of users, on the NPT Google Code site, similar to that developed for the GBIF IPT project will be available.

## Design and Implementation Constraints

CO1 The system shall be implemented using open-source technologies.

CO2 The system shall be written in PHP.

CO3 The system should be built in a modular way, which ensures that component functionalities can be adjusted, added, improved, removed or exchanged without impacting the application as a whole. Approaching the system using development best practices such as MVC (Model-View-Controller) can allow this sort of modularity.

CO4 The NPT development and implementation should follow design principles that will enable future growth, both in terms of the addition of new functionality or through modification of existing functionality. In addition, NPT developers should provide the possibility to consume services and functions that are created elsewhere. Examples include reference taxonomic data sources, mapping functions or web map services (WMS).

CO5 Sustainability embedded at each stage of development. The developers of the NPT should be mindful of the strategic implications of development choices to the long term sustainability of the NPT in a number of key areas: underlying hardware and software; development tools and frameworks; level of effort for system administrators and portal managers; level of interest and engagement of users, including researchers, data providers and other interested visitors.

## Interfaces

User Interfaces

Pagination

Long (more than 25) lists of items shall be paginated.

Distribution	  map

Distribution map shall allow the user to pan and to zoom in and out.

Filter	  building	  interface

While building a filter, visitors shall be presented the count of matching occurrences in real time (before launching the search).

Hardware Interfaces

No hardware interfaces have been identified.

Software Interfaces

Application	  programming	  interface

SI1.1 The system shall provide a Web service-based API to search and access core

resource metadata.

SI1.2 The system shall provide a Web service-based API to search and retrieve occurrence records.

SI1.3 The system shall provide a Web service-based API to search and retrieve taxa from the taxonomic backbone.

## GBIF	  IPT

SI2.1 The system shall poll IPT instances to retrieve the list of public core resources available.

SI2.2 The system shall poll IPT instances to retrieve core resources.

GBIF	  resource	  Web	  services

SI3.1 The system shall poll GBIF occurrence Web service to retrieve core resources.

GBIF	  Registry

SI4.1 The system shall poll GBIF Registry to retrieve the list of available extensions.

## Communications	  Interfaces

CI1 The system shall send an email to the portal contact person to forward visitor feedbacks.

CI2 The system shall send an email to data provider contact person to forward visitor feedbacks.

CI3 The system shall send an email to the data manager upon completion of a harvesting job.

CI4 The system shall send an email to the data manager upon completion of a backup operation.

CI5 The system shall send an email to the data manager upon completion of a backup restoration operation.

## Licensing Requirements

LR1 The system shall be released under an open-source compliant license.

LR2 The system shall use the same data usage agreement as GBIF portal.

## Glossary

API: an application programming interface (API) is a particular set of rules and specifications that software programs can follow to communicate with each other. It serves as an interface between different software programs and facilitates their interaction, similar to the way the user interface facilitates interaction between humans and computers. (source: Wikipedia)

Audit log: this log keeps track of all successful operations in the system front end. An audit log entry consists of the name of the operation, the name of the user who initiated the action and the date and time it occurred.

Backup report: report sent to the data manager once a backup operation is completed. If successful, the report contains statistics about the backup data and a link to the backup file.

<sub>•</sub> CMS: Content Management System.

<sub>•</sub> Core resource: an occurrence or checklist resource.

Darwin core: A standard consisting of terms and classes of terms used to share biodiversity data. (source: The GBIF Integrated Publishing Toolkit User Manual)

Darwin core archive (DwC-A): A single zipped archive for a data set consisting of one or more text files of data, an XML file describing the contents of the text files and how they relate to each other, and an XML file containing the dataset metadata in EML format. (source: The GBIF Integrated Publishing Toolkit User Manual)

Data usage log: A usage log entry contains the following information for each usage of the occurrence data: the date and time of the usage, the type ("mapped" or "exported") of the usage, the originating country, the number of occurrence records and a text representation of the filter used.

Data usage statistics: monthly statistics about the data visitors. They’re computed from the data usage logs.

Data metrics: data usage statistics and statistics about the data hosted on the portal i.e. data mass (number of occurrence records), taxonomic diversity (number of different taxa with occurrences).

EML: The Ecological Metadata Language is an XML-based profile used to encode metadata about a data set.

GIS: A geographic information system (GIS), geographical information system, or geospatial information system is a system designed to capture, store, manipulate, analyze, manage and present all types of geographically referenced data.

Harvesting job: the process of fetching core resources from registered data sources and updating the portal index with those data.

Harvesting report: a report containing success status and possible failure causes for each harvested data sources.

IPT: The Integrated Publishing Toolkit (IPT) is a deployable web-based tool that allows users to serve onto the Internet (or Intranet): primary biodiversity occurrence data [...], taxonomic checklist data [...] and higher-level dataset descriptive data (metadata) [...]. (source: Integrated Publishing Toolkit (IPT) - Architectural view)

Maintenance mode: the mode the system switches to when achieving certain operations that may prevent to deliver a satisfactory experience to the user in particular when the index may be inconsistent. When in that mode, all portal screens display an apology message informing the visitors that the portal is under maintenance and inviting them to wait a moment before trying to use it.

MVC: the Model View Controller is a software architecture pattern used in web applications to separate the concerns of data modeling, the rendering of the model for client consumption and the logic for accessing the content.

Report: a file generated when a consuming operation on core resource index has been completed. Such a file contains a success status, description on the job outcome and statistics about the core resource index after completion. In case of failure, the report indicates the cause.

Resource: In this document, a resource refers to a dataset and associated metadata. Resources handled by NPT instances are core resources, multimedia files, institutions, literature entries and experts.

Resource file: a file containing data for a resource (i.e. both records and metadata).

<sub>•</sub> Spatial layers: the geospatial layers displayed on the distribution map.

Taxonomic backbone: A specialized checklist, which is used to organize biodiversity data, indexed within the NPT, particularly occurrence data.

## Appendixes

Notes and conventions for use cases:

• Identifier of use cases start with ‘UC’ and sub flows with ‘S’.

an underlined phrase in a use case flow refers to the use case (or sub flow) with the same name.

standard (e.g. “log in” or “register”) or obvious (e.g. “view Network summary information”) functionalities haven’t been promoted as a use case but are nevertheless listed in the functionality requirement section.

Back end use cases

Administrator

A user may only initiate the use cases in this section if he is logged into the system using a user account with administrator role.

Manage	  modules

<table><tr><td colspan="1" rowspan="1">Identifier-Name</td><td colspan="3" rowspan="1">UC-A1 - Manage modules</td></tr><tr><td colspan="1" rowspan="1">Description</td><td colspan="3" rowspan="1">The administrator selects to manage modules so as to add newfunctionalities to the system by installing modules, configure or updatepreviously installed modules.</td></tr><tr><td colspan="1" rowspan="1">Actors</td><td colspan="3" rowspan="1">Administrator</td></tr><tr><td colspan="1" rowspan="1">Priority</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">Frequency</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="4" rowspan="1">Main flow</td></tr><tr><td colspan="1" rowspan="1">a</td><td colspan="3" rowspan="1">The use case starts when the administrator selects to manage modules.</td></tr><tr><td colspan="1" rowspan="1">b</td><td colspan="3" rowspan="1">The system retrieves the list of all installed modules and displays the list tothe administrator. The system provides two options for each module:update and configure. The system also displays the function install a newmodule.</td></tr><tr><td colspan="1" rowspan="1">C</td><td colspan="3" rowspan="1">The administrator selects to install a new module.</td></tr><tr><td colspan="1" rowspan="1">d</td><td colspan="3" rowspan="1">The system requests the administrator to provide the module file.</td></tr><tr><td colspan="1" rowspan="1">e</td><td colspan="3" rowspan="1">The administrator selects the module file on his local computer.</td></tr><tr><td colspan="1" rowspan="1">f</td><td colspan="3" rowspan="1">The system installs the module from the file.</td></tr><tr><td colspan="1" rowspan="1">g</td><td colspan="3" rowspan="1">The system records an audit log entry.</td></tr><tr><td colspan="1" rowspan="1">h</td><td colspan="3" rowspan="1">The system informs the administrator that the module has been successfullyinstalled.</td></tr><tr><td colspan="1" rowspan="1">i</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Alternate flows</td></tr><tr><td colspan="4" rowspan="1">Configure module</td></tr><tr><td colspan="1" rowspan="1">C1</td><td colspan="3" rowspan="1">The administrator selects the module of interest and chooses to configureit.</td></tr><tr><td colspan="1" rowspan="1">d1</td><td colspan="3" rowspan="1">The system requests the administrator to enter the configurationparameters specific to that module.</td></tr><tr><td colspan="1" rowspan="1">e1</td><td colspan="3" rowspan="1">The administrator enters the configuration parameters so the module fitsthe Node's needs.</td></tr><tr><td colspan="1" rowspan="1">f1</td><td colspan="3" rowspan="1">The system saves the module configuration.</td></tr><tr><td colspan="1" rowspan="1">g1</td><td colspan="3" rowspan="1">The system records an audit log entry.</td></tr><tr><td colspan="1" rowspan="1">h1</td><td colspan="3" rowspan="1">The system informs the administrator that the module has been successfullyconfigured.</td></tr><tr><td colspan="1" rowspan="1">i1</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Update module</td></tr><tr><td colspan="1" rowspan="1">c2</td><td colspan="3" rowspan="1">The administrator selects the module of interest and chooses the option toupdate it.</td></tr><tr><td colspan="1" rowspan="1">d2</td><td colspan="3" rowspan="1">The system requests the administrator to provide the module file.</td></tr><tr><td colspan="1" rowspan="1">e2</td><td colspan="3" rowspan="1">The administrator selects the module file on his local computer.</td></tr><tr><td colspan="1" rowspan="1">f2</td><td colspan="3" rowspan="1">The system installs the new version of the module from the file. The systemconfigures it with the parameters used for the previous version.</td></tr><tr><td colspan="1" rowspan="1">g2</td><td colspan="3" rowspan="1">The system records an audit log entry.</td></tr><tr><td colspan="1" rowspan="1">h2</td><td colspan="3" rowspan="1">The system informs admin the module has been successfully updated.</td></tr><tr><td colspan="1" rowspan="1">i2</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Exceptions</td></tr><tr><td colspan="4" rowspan="1">Handle error during module installation</td></tr><tr><td colspan="1" rowspan="1">f3</td><td colspan="3" rowspan="1">The system reports the installation failure to the administrator. The usecase ends.</td></tr><tr><td colspan="1" rowspan="1">g3</td><td colspan="3" rowspan="1">The system records an error log entry.</td></tr><tr><td colspan="1" rowspan="1">f3</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Handle error during module update</td></tr><tr><td colspan="1" rowspan="1">f2.1</td><td colspan="3" rowspan="1">The system reports the update failure to the administrator.</td></tr><tr><td colspan="1" rowspan="1">f2.2</td><td colspan="3" rowspan="1">The system records an error log entry.</td></tr><tr><td colspan="1" rowspan="1">f2.3</td><td colspan="3" rowspan="1">The use case ends.</td></tr></table>

Configure	  the	  distribution	  map

<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-A2 - Configure the distribution map</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The administrator selects to configure the distribution map so it uses thespecific projection and default extent for the Node area of interest.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Administrator</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>1</td></tr><tr><td rowspan=1 colspan=1>Post conditions</td><td rowspan=1 colspan=3>The distribution map will use the projection and default extent theadministrator chose.</td></tr><tr><td rowspan=1 colspan=1>Trigger</td><td rowspan=1 colspan=3>Upon NPT instance configuration, the administrator selects to configure thedistribution map.</td></tr><tr><td rowspan=1 colspan=1>Main flow</td><td rowspan=1 colspan=3></td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=3>The administrator selects to configure the distribution map.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=3>The system retrieves the list of standard projections and displays the list tothe administrator. The system requests the administrator to select theprojection and to enter the default extent for the map.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=3>The administrator enters the default extent and selects the projection thatwill be used by the distribution map from the list. The Portal managerupdates the system configuration.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=3>The system validates the provided default extent values.</td></tr><tr><td rowspan=1 colspan=1>e</td><td rowspan=1 colspan=3>The system updates its portal configuration with the new projection anddefault extent.</td></tr><tr><td rowspan=1 colspan=1>f</td><td rowspan=1 colspan=3>The system records an audit log entry.</td></tr><tr><td rowspan=1 colspan=1>g</td><td rowspan=1 colspan=3>The system informs the administrator the changes have successfully beensaved.</td></tr><tr><td rowspan=1 colspan=1>h</td><td rowspan=1 colspan=3>The use case ends.</td></tr><tr><td rowspan=1 colspan=4>Alternate flow</td></tr><tr><td rowspan=1 colspan=4>Handle invalid values for default extent</td></tr></table>

<table><tr><td>f3</td><td>The system informs the administrator that the values he entered for the map default extent are invalid. The system updates the portal configuration with the provided projection. The use case ends.</td></tr></table>

Manage	  spatial	  layers
<table><tr><td colspan="1" rowspan="1">Identifier-Name</td><td colspan="3" rowspan="1">UC-A3 - Manage spatial layers</td></tr><tr><td colspan="1" rowspan="1">Description</td><td colspan="3" rowspan="1">The administrator selects to add or delete the spatial layers displayed onthe distribution map for the specific Node.</td></tr><tr><td colspan="1" rowspan="1">Actors</td><td colspan="3" rowspan="1">Administrator</td></tr><tr><td colspan="1" rowspan="1">Priority</td><td colspan="1" rowspan="1">1</td><td colspan="1" rowspan="1">Frequency</td><td colspan="1" rowspan="1">3</td></tr><tr><td colspan="4" rowspan="1">Main flow (add a spatial layer)</td></tr><tr><td colspan="1" rowspan="1">a</td><td colspan="3" rowspan="1">The use case starts when the administrator selects to manage spatiallayers.</td></tr><tr><td colspan="1" rowspan="1">b</td><td colspan="3" rowspan="1">The system retrieves the list of all available spatial layers. The systemdisplays the list to the administrator with two options for each layer:“delete this layer" and “update this layer". The system offers a thirdfunction: “add a layer”.</td></tr><tr><td colspan="1" rowspan="1">C</td><td colspan="3" rowspan="1">The administrator chooses the option to add a new spatial layer.</td></tr><tr><td colspan="1" rowspan="1">d</td><td colspan="3" rowspan="1">The system requests the administrator to enter a name for the layer and toprovide the spatial layer file.</td></tr><tr><td colspan="1" rowspan="1">e</td><td colspan="3" rowspan="1">The administrator enters a name for the layer.</td></tr><tr><td colspan="1" rowspan="1">f</td><td colspan="3" rowspan="1">The administrator selects the spatial layer file on his local computer.</td></tr><tr><td colspan="1" rowspan="1">g</td><td colspan="3" rowspan="1">The system validates the spatial layer file.</td></tr><tr><td colspan="1" rowspan="1">h</td><td colspan="3" rowspan="1">The system saves the spatial layer.</td></tr><tr><td colspan="1" rowspan="1">i</td><td colspan="3" rowspan="1">The system records an audit log entry.</td></tr><tr><td colspan="1" rowspan="1">j</td><td colspan="3" rowspan="1">The system informs the administrator that the addition was successful.</td></tr><tr><td colspan="1" rowspan="1">k</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Alternate flows</td></tr><tr><td colspan="4" rowspan="1">Update a spatial layer.</td></tr><tr><td colspan="1" rowspan="1">c1</td><td colspan="3" rowspan="1">The administrator selects the spatial layer of interest and chooses theoption to update it.</td></tr><tr><td colspan="1" rowspan="1">d1</td><td colspan="3" rowspan="1">The system displays the spatial layer name. The system proposes theadministrator to edit the layer name and to provide a new version of thespatial layer file.</td></tr><tr><td colspan="1" rowspan="1">e1</td><td colspan="3" rowspan="1">The administrator edits the layer name and/or selects a spatial layer file onhis local computer.</td></tr><tr><td colspan="1" rowspan="1">f1</td><td colspan="3" rowspan="1">The use case resumes at step g.</td></tr><tr><td colspan="4" rowspan="1">Delete a spatial layer.</td></tr><tr><td colspan="1" rowspan="1">c2</td><td colspan="3" rowspan="1">The administrator selects the spatial layer of interest and chooses theoption to delete it.</td></tr><tr><td colspan="1" rowspan="1">d2</td><td colspan="3" rowspan="1">The system deletes the spatial layer.</td></tr><tr><td colspan="1" rowspan="1">e2</td><td colspan="3" rowspan="1">The system records an audit log entry.</td></tr><tr><td colspan="1" rowspan="1">f2</td><td colspan="3" rowspan="1">The system informs the administrator of the deletion success.</td></tr><tr><td colspan="1" rowspan="1">g2</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Exceptions</td></tr><tr><td colspan="4" rowspan="1">Handle corrupted file or file of an invalid format</td></tr><tr><td colspan="1" rowspan="1">f3</td><td colspan="3" rowspan="1">The system informs the administrator that the file corrupted or is not of aninvalid format and requests him to try again.</td></tr><tr><td colspan="1" rowspan="1">g3</td><td colspan="3" rowspan="1">The system records an error log entry.</td></tr><tr><td colspan="1" rowspan="1">f3</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">An error occurred during the spatial layer file import.</td></tr><tr><td colspan="1" rowspan="1">g4</td><td colspan="3" rowspan="1">The system informs the administrator the file could not be imported.</td></tr><tr><td colspan="1" rowspan="1">h4</td><td colspan="3" rowspan="1">The system records an error log entry.</td></tr><tr><td colspan="1" rowspan="1">i4</td><td colspan="3" rowspan="1">The use case ends.</td></tr></table>

Manage	  user	  accounts
<table><tr><td colspan="1" rowspan="1">Identifier-Name</td><td colspan="3" rowspan="1">UC-A4 - Manage user accounts</td></tr><tr><td colspan="1" rowspan="1">Description</td><td colspan="3" rowspan="1">The administrator performs this use case in order to create or deleteaccounts for the portal staff members. Depending on the roles theadministrator associates with those accounts, the users may be allowed toaccess restricted back end functionalities.</td></tr><tr><td colspan="1" rowspan="1">Actors</td><td colspan="3" rowspan="1">Administrator</td></tr><tr><td colspan="1" rowspan="1">Priority</td><td colspan="1" rowspan="1">4</td><td colspan="1" rowspan="1">Frequency</td><td colspan="1" rowspan="1">3</td></tr><tr><td colspan="4" rowspan="1">Main flow (create a user account)</td></tr><tr><td colspan="1" rowspan="1">a</td><td colspan="3" rowspan="1">The administrator selects to manage user accounts.</td></tr><tr><td colspan="1" rowspan="1">b</td><td colspan="3" rowspan="1">The system retrieves the list of user accounts and displays the list to theadministrator. For each user accounts, the system displays options to deleteand update the user account. The system also provides an option to create anew user account.</td></tr><tr><td colspan="1" rowspan="1">C</td><td colspan="3" rowspan="1">The administrator selects to create a new user account.</td></tr><tr><td colspan="1" rowspan="1">d</td><td colspan="3" rowspan="1">The system requests the security officer to enter user account information.</td></tr><tr><td colspan="1" rowspan="1">e</td><td colspan="3" rowspan="1">The administrator enters user account information.</td></tr><tr><td colspan="1" rowspan="1">f</td><td colspan="3" rowspan="1">The system displays the list of roles and requests the administrator to selectthe security roles for the user account.</td></tr><tr><td colspan="1" rowspan="1">g</td><td colspan="3" rowspan="1">The administrator selects the security roles for this user account.</td></tr><tr><td colspan="1" rowspan="1">h</td><td colspan="3" rowspan="1">The system verifies that no user account with the provided user namealready exists.</td></tr><tr><td colspan="1" rowspan="1">i</td><td colspan="3" rowspan="1">The system saves the user account.</td></tr><tr><td colspan="1" rowspan="1">j</td><td colspan="3" rowspan="1">The system records an audit log entry.</td></tr><tr><td colspan="1" rowspan="1">k</td><td colspan="3" rowspan="1">The system informs the administrator that the user account was successfullycreated.</td></tr><tr><td colspan="1" rowspan="1">1</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Alternate flow</td></tr><tr><td colspan="4" rowspan="1">Update a user account.</td></tr><tr><td colspan="1" rowspan="1">c1</td><td colspan="3" rowspan="1">The data manager selects the user account of interest and chooses theoption to update it.</td></tr><tr><td colspan="1" rowspan="1">d1</td><td colspan="3" rowspan="1">The system displays the user account information associated with thisaccount and requests the administrator to edit the user account password orcontact email address.</td></tr><tr><td colspan="1" rowspan="1">e1</td><td colspan="3" rowspan="1">If needed, the administrator edits the user account information.</td></tr><tr><td colspan="1" rowspan="1">f1</td><td colspan="3" rowspan="1">The system displays the list of roles. Each role is preselected if the useraccount is associated with it. For each role, the system provides the optionto select or unselect it. The system requests the security officer to selectthe security roles this user account will be associated with.</td></tr><tr><td colspan="1" rowspan="1">g1</td><td colspan="3" rowspan="1">The administrator selects the security roles to be associated with that useraccount.</td></tr><tr><td colspan="1" rowspan="1">h1</td><td colspan="3" rowspan="1">The system updates the user account.</td></tr><tr><td colspan="1" rowspan="1">i1</td><td colspan="3" rowspan="1">The system records an audit log entry.</td></tr><tr><td colspan="1" rowspan="1">j1</td><td colspan="3" rowspan="1">The system informs the administrator of the update success.</td></tr><tr><td colspan="1" rowspan="1">k1</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Delete a user account.</td></tr><tr><td colspan="1" rowspan="1">c2</td><td colspan="3" rowspan="1">The administrator selects the user account of interest and chooses theoption to delete it.</td></tr><tr><td colspan="1" rowspan="1">d2</td><td colspan="3" rowspan="1">The system deletes the user account.</td></tr><tr><td colspan="1" rowspan="1">i1</td><td colspan="3" rowspan="1">The system records an audit log entry.</td></tr><tr><td colspan="1" rowspan="1">j1</td><td colspan="3" rowspan="1">The system informs the administrator of the deletion success.</td></tr><tr><td colspan="1" rowspan="1">k1</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">A user account with that user name already exists.</td></tr><tr><td colspan="1" rowspan="1">h3</td><td colspan="3" rowspan="1">A user account with that user name already exists; the system informs theadministrator that the user account could not be created because the username already exists. The use case returns to step b.</td></tr></table>

## Data	  manager

A user may only initiate the use cases in this section if he is logged into the system using a user account with data manager role.

Manage	  resources

<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-DM1 - Manage resources</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The data manager wants to manage resources so as to import a newresource, edit a resource metadata or delete a resource.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Data manager</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>3</td></tr><tr><td rowspan=1 colspan=4>Main flow (import a resource)</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=3>The use case starts when the data manager selects to manage resources.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=3>The system displays the list of available resource types (occurrence,checklist, institution, multimedia, literature or expert). The systemrequests the data manager to select the type of resource he wishes tomanage.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=3>The data manager selects the type of resources to manage.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=3>The system retrieves the list of resources of that type.</td></tr><tr><td rowspan=1 colspan=1>e</td><td rowspan=1 colspan=3>The system displays the list to the data manager with two options for eachresource: delete and edit metadata. The system also displays two high levelfunctions: import a resource and search resources.</td></tr><tr><td rowspan=1 colspan=1>f</td><td rowspan=1 colspan=3>The data manager chooses the option to import a resource.</td></tr><tr><td rowspan=1 colspan=1>g</td><td rowspan=1 colspan=3>The system requests the data manager to provide the resource file and ashort name for the resource.</td></tr><tr><td rowspan=1 colspan=1>h</td><td rowspan=1 colspan=3>The data manager selects the resource file from his local computer andenters a short name.</td></tr><tr><td rowspan=1 colspan=1>i</td><td rowspan=1 colspan=3>The system validates the resource file.</td></tr><tr><td rowspan=1 colspan=1>j</td><td rowspan=1 colspan=3>The system archives the resource file. The system extracts the records andmetadata from the file and saves them.</td></tr><tr><td rowspan=1 colspan=1>k</td><td rowspan=1 colspan=3>The system records an audit log entry.</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=3>The system informs the data manager that the import was successful.</td></tr><tr><td rowspan=1 colspan=1>m</td><td rowspan=1 colspan=3>The use case ends.</td></tr><tr><td rowspan=1 colspan=4>Alternate flows</td></tr><tr><td rowspan=1 colspan=4>Edit a resource metadata.</td></tr></table>

<table><tr><td rowspan=1 colspan=1>f1</td><td rowspan=1 colspan=1>The data manager selects the resource of interest and chooses the option toedit its metadata.</td></tr><tr><td rowspan=1 colspan=1>g1</td><td rowspan=1 colspan=1>The system retrieves the resource metadata. The system displays themetadata to the data manager.</td></tr><tr><td rowspan=1 colspan=1>h1</td><td rowspan=1 colspan=1>The data manager edits the metadata.</td></tr><tr><td rowspan=1 colspan=1>i1</td><td rowspan=1 colspan=1>The system records an audit log entry.</td></tr><tr><td rowspan=1 colspan=1>j1</td><td rowspan=1 colspan=1>The system saves the metadata. The use case ends.</td></tr><tr><td rowspan=1 colspan=2>Delete a resource.</td></tr><tr><td rowspan=1 colspan=1>f2</td><td rowspan=1 colspan=1>The data manager selects a resource and chooses the option to delete it.</td></tr><tr><td rowspan=1 colspan=1>g2</td><td rowspan=1 colspan=1>The system asks the data manager for confirmation.</td></tr><tr><td rowspan=1 colspan=1>h2</td><td rowspan=1 colspan=1>The data manager confirms deletion.</td></tr><tr><td rowspan=1 colspan=1>i2</td><td rowspan=1 colspan=1>The system records an audit log entry.</td></tr><tr><td rowspan=1 colspan=1>j2</td><td rowspan=1 colspan=1>The system deletes the resource records and its metadata. The systemdeletes the archived resource file. The system informs the data manager ofthe deletion success. The use case ends.</td></tr><tr><td rowspan=1 colspan=2>Search resources.</td></tr><tr><td rowspan=1 colspan=1>d3</td><td rowspan=1 colspan=1>The data manager selects to search secondary resource of interest.</td></tr><tr><td rowspan=1 colspan=1>e3</td><td rowspan=1 colspan=1>The system requests the data manager to enter a keyword query.</td></tr><tr><td rowspan=1 colspan=1>f3</td><td rowspan=1 colspan=1>The data manager enters the keywords and launches search.</td></tr><tr><td rowspan=1 colspan=1>g3</td><td rowspan=1 colspan=1>The system records an audit log entry.</td></tr><tr><td rowspan=1 colspan=1>h3</td><td rowspan=1 colspan=1>The system retrieves the list of resources which metadata match thekeyword query. The use case resumes at step c.</td></tr><tr><td rowspan=1 colspan=2>Cancel resource deletion.</td></tr><tr><td rowspan=1 colspan=1>h2.1</td><td rowspan=1 colspan=1>The data manager cancels deletion. The use case ends.</td></tr><tr><td rowspan=1 colspan=2>Exception</td></tr><tr><td rowspan=1 colspan=2>Handle corrupted file or file of an invalid format</td></tr><tr><td rowspan=1 colspan=1>i4</td><td rowspan=1 colspan=1>The system informs the data manager that the import operation failedbecause the provided file was corrupted or have an invalid format.</td></tr><tr><td rowspan=1 colspan=1>j4</td><td rowspan=1 colspan=1>The system records an error log entry.</td></tr><tr><td rowspan=1 colspan=1>k4</td><td rowspan=1 colspan=1>The use case ends.</td></tr></table>

Register	  a	  new	  data	  source
<table><tr><td colspan="1" rowspan="1">Identifier-Name</td><td colspan="3" rowspan="1">UC-DM2 - Register a new data source</td></tr><tr><td colspan="1" rowspan="1">Description</td><td colspan="3" rowspan="1">The data manager registers a new data source so the associated coreresource is harvested during next harvesting job.</td></tr><tr><td colspan="1" rowspan="1">Actors</td><td colspan="3" rowspan="1">Data manager - Secondary: Data source</td></tr><tr><td colspan="1" rowspan="1">Priority</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">Frequency</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="1" rowspan="1">Main flow</td><td colspan="3" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">a</td><td colspan="3" rowspan="1">The use case starts when the data manager selects to register a data source.</td></tr><tr><td colspan="1" rowspan="1">b</td><td colspan="3" rowspan="1">The data manager selects to add a new data source.</td></tr><tr><td colspan="1" rowspan="1">C</td><td colspan="3" rowspan="1">The system displays the list of available data source types to the datamanager. The system requests the data manager to select a type andprovide a name and a URL for the source.</td></tr><tr><td colspan="1" rowspan="1">d</td><td colspan="3" rowspan="1">Data manager selects the type and enters a name for the source.</td></tr><tr><td colspan="1" rowspan="1">e</td><td colspan="3" rowspan="1">The system requests the data manager to enter the specific configurationparameters for this source type.</td></tr><tr><td colspan="1" rowspan="1">f</td><td colspan="3" rowspan="1">Data manager enters the configuration parameters.</td></tr><tr><td colspan="1" rowspan="1">g</td><td colspan="3" rowspan="1">The system sends a request to the data source.</td></tr><tr><td colspan="1" rowspan="1">h</td><td colspan="3" rowspan="1">The data source responds with a success OK code.</td></tr><tr><td colspan="1" rowspan="1">i</td><td colspan="3" rowspan="1">The system saves the new data source to its source registry. The systeminforms the data manager of the addition success.</td></tr><tr><td colspan="1" rowspan="1">j</td><td colspan="3" rowspan="1">The system records an audit log entry.</td></tr><tr><td colspan="1" rowspan="1">k</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Exceptions</td></tr><tr><td colspan="4" rowspan="1">Handle communication failure with the data source.</td></tr><tr><td colspan="1" rowspan="1">h1</td><td colspan="3" rowspan="1">If the system cannot communicate with the data source, the system informsthe data manager that the data source cannot be added because the sourceis not accessible.</td></tr><tr><td colspan="1" rowspan="1">i1</td><td colspan="3" rowspan="1">The system records an error log entry.</td></tr><tr><td colspan="1" rowspan="1">j1</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Handle a response with an error code.</td></tr><tr><td colspan="1" rowspan="1">h2</td><td colspan="3" rowspan="1">If the data source responded with an error code, the system informs thedata manager that the data source cannot be added because the sourceresponded with an error code.</td></tr><tr><td colspan="1" rowspan="1">i2</td><td colspan="3" rowspan="1">The system records an error log entry.</td></tr><tr><td colspan="1" rowspan="1">j2</td><td colspan="3" rowspan="1">The use case ends.</td></tr></table>

Register	  a	  GBIF	  index	  data	  source
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-DM3 - Register a GBIF index data source</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>Specializes Register a new data source to allow specific configuration forGBIF occurrence Web services data sources.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Data manager - Secondary: GBIF Web services</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr><tr><td rowspan=1 colspan=4>Main flow</td></tr><tr><td rowspan=1 colspan=1>f3</td><td rowspan=1 colspan=3>The visitor enters the request parameters that will be used to query GBIFportal API. The use case resumes at step g.</td></tr></table>

Register	  an	  IPT	  data	  source
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-DM4 - Register an IPT data source</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>Specializes Register a new data source to allow specific configuration for IPTdata sources.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Data manager - Secondary: IPT data source</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>2</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr><tr><td rowspan=1 colspan=4>Main flow</td></tr><tr><td rowspan=1 colspan=1>f4.1</td><td rowspan=1 colspan=3>The data manager enters the URL of the IPT instance hosting the datasource of interest.</td></tr><tr><td rowspan=1 colspan=1>f4.2</td><td rowspan=1 colspan=3>The system calls the IPT instance for the list of hosted public coreresources.</td></tr><tr><td rowspan=1 colspan=1>f4.3</td><td rowspan=1 colspan=3>The IPT instance returns the resource list to the system.</td></tr><tr><td rowspan=1 colspan=1>f4.4</td><td rowspan=1 colspan=3>The system displays this list of resources to the data manager. The systemrequests the data manager to select the core resource he wishes toregister.</td></tr><tr><td rowspan=1 colspan=1>f4.5</td><td rowspan=1 colspan=3>The data manager selects the core resource. The use case resumes at stepg.</td></tr></table>

Unregister	  a	  data	  source
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-DM5 - Unregister a data source</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The data manager previously added a data source which is no more relevantto the node or not available any more. The data manager wants tounregister this source.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Data manager</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr><tr><td rowspan=1 colspan=1>Post conditions</td><td rowspan=1 colspan=3>The data source has been removed from the system configuration. Duringnext harvesting job, no occurrence records will be harvested from this datasource.</td></tr><tr><td rowspan=1 colspan=4>Main flow</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=3>The use case starts when the data manager selects to unregister a datasource.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=3>The data manager selects the source of interest and chooses the option tounregister it.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=3>The system prompts the user for confirmation and displays an option to alsodelete related occurrence records from the index.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=3>The data manager confirms that he wishes to unregister the selected datasource and selects the option to delete related occurrence records from theindex.</td></tr><tr><td rowspan=1 colspan=1>e</td><td rowspan=1 colspan=3>The system deletes occurrence records that were harvested from thissource.</td></tr><tr><td rowspan=1 colspan=1>f</td><td rowspan=1 colspan=3>The system removes this source from its registry.</td></tr><tr><td rowspan=1 colspan=1>g</td><td rowspan=1 colspan=3>The system records an audit log entry.</td></tr><tr><td rowspan=1 colspan=1>h</td><td rowspan=1 colspan=3>The use case ends.</td></tr><tr><td rowspan=1 colspan=4>Alternate flows</td></tr><tr><td rowspan=1 colspan=4>Cancel to unregister the data source.</td></tr><tr><td rowspan=1 colspan=1>d1</td><td rowspan=1 colspan=3>The data manager chooses to cancel unregistering the data source. The usecase ends.</td></tr><tr><td rowspan=1 colspan=1>Unregister data so</td><td rowspan=1 colspan=3>urce but keep related occurrence records.</td></tr><tr><td rowspan=1 colspan=1>d2</td><td rowspan=1 colspan=3>If the data manager confirms data source deletion but doesn&#x27;t select theoption to delete related occurrence records from the index. The use caseresumes to step g.</td></tr></table>

Manage	  harvesting	  jobs
<table><tr><td colspan="1" rowspan="1">Identifier-Name</td><td colspan="3" rowspan="1">UC-DM6 - Manage harvesting jobs</td></tr><tr><td colspan="1" rowspan="1">Description</td><td colspan="3" rowspan="1">The data manager wants to manage jobs so as to monitor finished andupcoming jobs, schedule a new job or cancel a scheduled job.</td></tr><tr><td colspan="1" rowspan="1">Actors</td><td colspan="3" rowspan="1">Data manager</td></tr><tr><td colspan="1" rowspan="1">Priority</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">Frequency</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="4" rowspan="1">Main flow (schedule a new harvesting job)</td></tr><tr><td colspan="1" rowspan="1">a</td><td colspan="3" rowspan="1">The use case starts when the data manager chooses the option to manageharvesting jobs.</td></tr><tr><td colspan="1" rowspan="1">b</td><td colspan="3" rowspan="1">The system retrieves two lists of jobs: finished and forthcoming jobs. Thesystem displays the lists to the data manager. For the former, an option to</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="3" rowspan="1">view the associated harvesting report is provided. For the latter, the systemdisplays a cancel option for each job. The system also offers the functionschedule a new job.</td></tr><tr><td colspan="1" rowspan="1">C</td><td colspan="3" rowspan="1">The data manager chooses to schedule a new job.</td></tr><tr><td colspan="1" rowspan="1">d</td><td colspan="3" rowspan="1">The system requests the data manager to provide date and time for the newjob.</td></tr><tr><td colspan="1" rowspan="1">e</td><td colspan="3" rowspan="1">Data manager enters the new job date and time.</td></tr><tr><td colspan="1" rowspan="1">f</td><td colspan="3" rowspan="1">The system saves the new job.</td></tr><tr><td colspan="1" rowspan="1">g</td><td colspan="3" rowspan="1">The system records an audit log entry.</td></tr><tr><td colspan="1" rowspan="1">h</td><td colspan="3" rowspan="1">The system informs the data manager that the job has successfully beenscheduled.</td></tr><tr><td colspan="1" rowspan="1">i</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Alternate flows</td></tr><tr><td colspan="4" rowspan="1">Cancel a job.</td></tr><tr><td colspan="1" rowspan="1">c1</td><td colspan="3" rowspan="1">The data manager selects the job of interest and chooses the option tocancel it.</td></tr><tr><td colspan="1" rowspan="1">d1</td><td colspan="3" rowspan="1">The system deletes the job. The use case ends.</td></tr><tr><td colspan="4" rowspan="1">View harvesting report for a job.</td></tr><tr><td colspan="1" rowspan="1">c2</td><td colspan="3" rowspan="1">The data manager selects the job of interest and chooses the option to viewthe harvesting report associated to it.</td></tr><tr><td colspan="1" rowspan="1">d2</td><td colspan="3" rowspan="1">The system displays the harvesting report for this job to the data manager.The use case ends.</td></tr></table>

Retrieve	  the	  list	  of	  updated	  data	  sources
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=1>S-DM1 - Retrieve the list of data sources updated since last harvesting job</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=1>The system builds two lists: updated and unavailable data sources.</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=1>The system retrieves the list of registered data sources.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=1>The system picks a data source.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=1>The system requests this data source to return the version number of theassociated core resource.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=1>The data source returns the version number of its core resource.</td></tr><tr><td rowspan=1 colspan=1>e</td><td rowspan=1 colspan=1>If the version number doesn&#x27;t match the one of the local core resource, thesystem adds the source to the list of updated data sources.</td></tr><tr><td rowspan=1 colspan=1>f</td><td rowspan=1 colspan=1>Step c to f repeats for all registered data sources.</td></tr><tr><td rowspan=1 colspan=1>g</td><td rowspan=1 colspan=1>Return to the next step.</td></tr><tr><td rowspan=1 colspan=2>Exception</td></tr><tr><td rowspan=1 colspan=2>Handle communication failure with the data source.</td></tr><tr><td rowspan=1 colspan=1>d1</td><td rowspan=1 colspan=1>If the system cannot communicate with the data source, the system addsthe data source to the list of unavailable data sources.</td></tr><tr><td rowspan=1 colspan=1>e1</td><td rowspan=1 colspan=1>The system records an error log entry.</td></tr><tr><td rowspan=1 colspan=1>f1</td><td rowspan=1 colspan=1>The sub flow resumes at step c.</td></tr></table>

Check	  core	  resources	  consistency	  with	  registered	  data	  sources

<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=1>UC-DM7 - Check core resources consistency with registered data sources</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=1>The data manager checks core resources consistency with registered datasources to identify outdated core resources and unavailable data sources.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=1>Data manager - Secondary: Registered occurrence data source</td></tr></table>

<table><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>3</td></tr><tr><td rowspan=1 colspan=1>Preconditions</td><td rowspan=1 colspan=3>At least one data source has been registered.At least one harvesting job has been successfully carried out.</td></tr><tr><td rowspan=1 colspan=4>Main flow</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=3>Data manager selects to check occurrence data consistency.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=3>Perform Retrieve the list of updated data sources.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=3>The system displays two lists to the data manager: updated and unavailabledata sources.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=3>The system records an audit log entry.</td></tr><tr><td rowspan=1 colspan=1>e</td><td rowspan=1 colspan=3>The use case ends.</td></tr></table>

Trigger	  a	  harvesting	  job
<table><tr><td colspan="1" rowspan="1">Identifier-Name</td><td colspan="3" rowspan="1">UC-DM8 - Trigger a harvesting job</td></tr><tr><td colspan="1" rowspan="1">Description</td><td colspan="3" rowspan="1">The data manager selects to trigger a harvesting job so as to synchronizethe portal biodiversity data with those hosted on the registered datasources.</td></tr><tr><td colspan="1" rowspan="1">Actors</td><td colspan="3" rowspan="1">Primary: Data manager - Secondary: Data sources</td></tr><tr><td colspan="1" rowspan="1">Priority</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">Frequency</td><td colspan="1" rowspan="1">3</td></tr><tr><td colspan="1" rowspan="1">Preconditions</td><td colspan="3" rowspan="1">At least one data source has been added.</td></tr><tr><td colspan="1" rowspan="1">Post conditions</td><td colspan="3" rowspan="1">The local occurrence index is consistent with all configured data sourceindex.</td></tr><tr><td colspan="4" rowspan="1">Main Flow</td></tr><tr><td colspan="1" rowspan="1">a</td><td colspan="3" rowspan="1">The use case starts when the data manager selects to trigger a harvestingjob.</td></tr><tr><td colspan="1" rowspan="1">b</td><td colspan="3" rowspan="1">The system adds a new job to the harvesting schedule with the current dateand time.</td></tr><tr><td colspan="1" rowspan="1">C</td><td colspan="3" rowspan="1">Perform Retrieve the list of updated data sources</td></tr><tr><td colspan="1" rowspan="1">d</td><td colspan="3" rowspan="1">The system picks a resource from the updated data source list.</td></tr><tr><td colspan="1" rowspan="1">e</td><td colspan="3" rowspan="1">The system requests this resource originating data source to return theassociated resource file.</td></tr><tr><td colspan="1" rowspan="1">f</td><td colspan="3" rowspan="1">The data source returns the core resource file.</td></tr><tr><td colspan="1" rowspan="1">g</td><td colspan="3" rowspan="1">The system validates and archives the core resource file.</td></tr><tr><td colspan="1" rowspan="1">h</td><td colspan="3" rowspan="1">The system repeats steps d to g for all data sources in the list.</td></tr><tr><td colspan="1" rowspan="1">i</td><td colspan="3" rowspan="1">The system switches to maintenance mode.</td></tr><tr><td colspan="1" rowspan="1">j</td><td colspan="3" rowspan="1">The system updates its index with harvested data.</td></tr><tr><td colspan="1" rowspan="1">k</td><td colspan="3" rowspan="1">The system switches back to normal mode.</td></tr><tr><td colspan="1" rowspan="1">1</td><td colspan="3" rowspan="1">The system records an audit log entry.</td></tr><tr><td colspan="1" rowspan="1">m</td><td colspan="3" rowspan="1">The system sets job status to “finished"and success status to “success"</td></tr><tr><td colspan="1" rowspan="1">n</td><td colspan="3" rowspan="1">The system sends a harvesting report to the data manager by email.</td></tr><tr><td colspan="1" rowspan="1">0</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Exceptions</td></tr><tr><td colspan="4" rowspan="1">Handle communication failure with the data source.</td></tr><tr><td colspan="1" rowspan="1">f1</td><td colspan="3" rowspan="1">If the system cannot communicate with the data source, the system addsthe data source to the list of unharvested data sources.</td></tr><tr><td colspan="1" rowspan="1">g1</td><td colspan="3" rowspan="1">The system records an error log entry.</td></tr><tr><td colspan="1" rowspan="1">h1</td><td colspan="3" rowspan="1">The use case resumes at step d.</td></tr><tr><td colspan="1" rowspan="1">Handle corrupted r</td><td colspan="3" rowspan="1">esource file.</td></tr><tr><td colspan="1" rowspan="1">e2</td><td colspan="3" rowspan="1">If the file served by the source is corrupted, the system adds the data</td></tr><tr><td></td><td colspan="3">source to the list of unharvested data sources.</td></tr><tr><td>f2</td><td colspan="3">The system records an error log entry.</td></tr><tr><td>g2</td><td colspan="3">The use case resumes at step d.</td></tr><tr><td>Handle indexes update error</td><td colspan="3"></td></tr><tr><td>j3</td><td colspan="3">If an error occurs while updating all indexes referring to entries in the taxonomic backbone, the system rollbacks. The system adds the data source</td></tr><tr><td>k3</td><td colspan="3">to the list of unharvested data sources. The system records an error log entry.</td></tr><tr><td>13</td><td colspan="3">The use case resumes at step d.</td></tr></table>

Update	  taxonomic	  backbone
<table><tr><td colspan="1" rowspan="1">Identifier-Name</td><td colspan="3" rowspan="1">UC-DM9 - Update taxonomic backbone</td></tr><tr><td colspan="1" rowspan="1">Description</td><td colspan="3" rowspan="1">The data manager updates the taxonomic backbone with a checklistresource.</td></tr><tr><td colspan="1" rowspan="1">Actors</td><td colspan="3" rowspan="1">Data manager</td></tr><tr><td colspan="1" rowspan="1">Priority</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">Frequency</td><td colspan="1" rowspan="1">3</td></tr><tr><td colspan="1" rowspan="1">Preconditions</td><td colspan="3" rowspan="1">A file containing the checklist resource to be used as the new taxonomicbackbone is stored on the data manager's local computer.</td></tr><tr><td colspan="4" rowspan="1">Main flow</td></tr><tr><td colspan="1" rowspan="1">a</td><td colspan="3" rowspan="1">The use case starts when the data manager selects to update the systemtaxonomic backbone.</td></tr><tr><td colspan="1" rowspan="1">b</td><td colspan="3" rowspan="1">The system requests the data manager to provide a file containing thechecklist resource to replace the taxonomic backbone with.</td></tr><tr><td colspan="1" rowspan="1">C</td><td colspan="3" rowspan="1">The data manager selects the file containing the new taxonomic backbonefrom his local computer.</td></tr><tr><td colspan="1" rowspan="1">d</td><td colspan="3" rowspan="1">The system validates the file.</td></tr><tr><td colspan="1" rowspan="1">e</td><td colspan="3" rowspan="1">The system informs the data manager that the process may be long and thatan email will be sent to him upon completion.</td></tr><tr><td colspan="1" rowspan="1">f</td><td colspan="3" rowspan="1">The system switches to maintenance mode.</td></tr><tr><td colspan="1" rowspan="1">g</td><td colspan="3" rowspan="1">The system updates its taxonomic backbone with the chosen checklistresource.</td></tr><tr><td colspan="1" rowspan="1">h</td><td colspan="3" rowspan="1">The system updates all indexes referring to entries in the taxonomicbackbone to ensure index consistency.</td></tr><tr><td colspan="1" rowspan="1">i</td><td colspan="3" rowspan="1">The system records an audit log entry.</td></tr><tr><td colspan="1" rowspan="1">j</td><td colspan="3" rowspan="1">The system switches back to normal mode.</td></tr><tr><td colspan="1" rowspan="1">k</td><td colspan="3" rowspan="1">The system sends a taxonomic backbone update report with a ‘success'status to the data manager by email.</td></tr><tr><td colspan="1" rowspan="1">1</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Exceptions</td></tr><tr><td colspan="4" rowspan="1">Handle corrupted file or file of an invalid format</td></tr><tr><td colspan="1" rowspan="1">d1</td><td colspan="3" rowspan="1">If the file provided by the data manager is corrupted or of an invalidformat, the system sends the data manager a backup restoration reportwith a ‘failure'status by email.</td></tr><tr><td colspan="1" rowspan="1">e1</td><td colspan="3" rowspan="1">The system records an error log entry.</td></tr><tr><td colspan="1" rowspan="1">f1</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Handle taxonomic backbone index update error</td></tr><tr><td colspan="1" rowspan="1">g2</td><td colspan="3" rowspan="1">If an error occurs while updating the taxonomic backbone index, the systemrollbacks. The system sends an email to the data manager containing abackup restoration report with a ‘failure'status.</td></tr><tr><td colspan="1" rowspan="1">f2</td><td colspan="3" rowspan="1">The system records an error log entry.</td></tr><tr><td colspan="1" rowspan="1">g2</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Handle indexes update error</td></tr><tr><td colspan="1" rowspan="1">h3</td><td colspan="3" rowspan="1">If an error occurs while updating all indexes referring to entries in thetaxonomic backbone, the system rollbacks. The system sends an email tothe data manager containing a backup restoration report with a ‘failure'status.</td></tr><tr><td colspan="1" rowspan="1">i3</td><td colspan="3" rowspan="1">The system records an error log entry.</td></tr><tr><td colspan="1" rowspan="1">j3</td><td colspan="3" rowspan="1">The use case ends.</td></tr></table>

Install	  an	  extension

<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-DM10 - Install an extension</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The data manager wants to install an extension to allow the system to dealwith extra attributes for records of core resources.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Primary: Data manager - Secondary: GBIF registry</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>3</td></tr><tr><td rowspan=1 colspan=4>Main flow</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=3>The use case starts when the data manager chooses the option to manageextensions.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=3>The system retrieves the list of installed extensions from its local registryand displays the list to the data manager.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=3>The data manager chooses to install a new extension.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=3>The system requests the GBIF registry for the lists of extensions.</td></tr><tr><td rowspan=1 colspan=1>e</td><td rowspan=1 colspan=3>GBIF registry returns the list of all available extensions along with theirURLs.</td></tr><tr><td rowspan=1 colspan=1>f</td><td rowspan=1 colspan=3>The system removes the list of already installed extensions from this list.The system displays this list to the data manager.</td></tr><tr><td rowspan=1 colspan=1>g</td><td rowspan=1 colspan=3>The data manager chooses the extension to install.</td></tr><tr><td rowspan=1 colspan=1>h</td><td rowspan=1 colspan=3>The system calls the GBIF registry for the extension.</td></tr><tr><td rowspan=1 colspan=1>i</td><td rowspan=1 colspan=3>The GBIF registry returns the extension to the system.</td></tr><tr><td rowspan=1 colspan=1>j</td><td rowspan=1 colspan=3>The system saves the extension and adds it to its local registry. The systemcreates an index for the data type or extra attributes defined by thisextension.</td></tr><tr><td rowspan=1 colspan=1>k</td><td rowspan=1 colspan=3>The system records an audit log entry.</td></tr><tr><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=3>The system informs the data manager that the installation was successful.</td></tr><tr><td rowspan=1 colspan=1>m</td><td rowspan=1 colspan=3>The use case ends.</td></tr></table>

## Portal	  manager

A user may only initiate the use cases in this section if he is logged into the system using an account with portal manager role.

Configure	  data	  metrics	  visibility

<table><tr><td>Identifier-Name</td><td colspan="3">UC-PM3 - Configure data metrics visibility</td></tr><tr><td colspan="1" rowspan="1">Description</td><td colspan="3" rowspan="1">The portal manager configures data metrics visibility in order to hide somemetrics from the visitors.</td></tr><tr><td colspan="1" rowspan="1">Actors</td><td colspan="3" rowspan="1">Portal manager</td></tr><tr><td colspan="1" rowspan="1">Priority</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">Frequency</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">Post conditions</td><td colspan="3" rowspan="1">The data metrics not declared as visible by the portal manager are hiddento the portal visitors.</td></tr><tr><td colspan="4" rowspan="1">Main flow</td></tr><tr><td colspan="1" rowspan="1">a</td><td colspan="3" rowspan="1">The use case starts when the portal manager selects to configure datametrics public availability.</td></tr><tr><td colspan="1" rowspan="1">b</td><td colspan="3" rowspan="1">The system displays the list of all data metrics and associated visibilitystatus to the data manager.</td></tr><tr><td colspan="1" rowspan="1">C</td><td colspan="3" rowspan="1">The portal manager selects the desired visibility status for each datametrics.</td></tr><tr><td colspan="1" rowspan="1">d</td><td colspan="3" rowspan="1">The system updates its configuration with the new visibility status for thedata metrics.</td></tr><tr><td colspan="1" rowspan="1">e</td><td colspan="3" rowspan="1">The system records an audit log entry.</td></tr><tr><td colspan="1" rowspan="1">f</td><td colspan="3" rowspan="1">The use case ends.</td></tr></table>

Customize	  NPT	  instance
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-PM2 - Customize NPT instance</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The portal manager customizes the NPT instance to adapt the portalappearance and parameters to fit its organization.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Portal manager</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>1</td></tr><tr><td rowspan=1 colspan=1>Post conditions</td><td rowspan=1 colspan=3>The system displays the node banner, logo and custom information on theportal.</td></tr><tr><td rowspan=1 colspan=4>Main flow (Customize NPT institutional information)</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=3>The use case starts when the portal manager selects to configureinstitutional information.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=3>The system displays two functions: customize “look and feel” and configureportal.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=3>The portal manager chooses to configure the portal.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=3>The system requests the portal manager to enter the node name, Networksummary information (in all front office languages) and contact person&#x27;sname and email address, and HTML metadata tags</td></tr><tr><td rowspan=1 colspan=1>e</td><td rowspan=1 colspan=3>The portal manager enters this information.</td></tr><tr><td rowspan=1 colspan=1>f</td><td rowspan=1 colspan=3>The system updates the NPT configuration with the new parameters.</td></tr><tr><td rowspan=1 colspan=1>g</td><td rowspan=1 colspan=3>The system records an audit log entry.</td></tr><tr><td rowspan=1 colspan=1>h</td><td rowspan=1 colspan=3>The use case ends.</td></tr><tr><td rowspan=1 colspan=4>Alternate flow</td></tr><tr><td rowspan=1 colspan=4>Customize “look and feel&quot;</td></tr><tr><td rowspan=1 colspan=1>d1</td><td rowspan=1 colspan=3>The system requests the portal manager to provide files for theorganization logo and the portal banner image.</td></tr><tr><td rowspan=1 colspan=1>e1</td><td rowspan=1 colspan=3>The portal manager selects the logo and/or banner image files on his localcomputer. The use case resumes at step f.</td></tr></table>

Configure	  front	  office	  languages

<table><tr><td>Identifier-Name</td><td colspan="3">UC-PM3 - Configure front office languages</td></tr><tr><td colspan="1" rowspan="1">Description</td><td colspan="3" rowspan="1">The data manager selects to manage front office languages so as to set thedefault and alternate portal languages.</td></tr><tr><td colspan="1" rowspan="1">Actors</td><td colspan="3" rowspan="1">Portal manager</td></tr><tr><td colspan="1" rowspan="1">Priority</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">Frequency</td><td colspan="1" rowspan="1">2</td></tr><tr><td colspan="4" rowspan="1">Main flow (list text documents)</td></tr><tr><td colspan="1" rowspan="1">a</td><td colspan="3" rowspan="1">The use case starts when the portal manager selects to manage front officelanguages.</td></tr><tr><td colspan="1" rowspan="1">b</td><td colspan="3" rowspan="1">The system retrieves the list of all installed languages.The system displays the default language and the list of alternate languagesand two options: change the default language and install a new language.For each alternate language, the system displays two options: uninstall andset as default.</td></tr><tr><td colspan="1" rowspan="1">C</td><td colspan="3" rowspan="1">The data manager selects to change the default language.</td></tr><tr><td colspan="1" rowspan="1">d</td><td colspan="3" rowspan="1">The system displays the list of all installed non-default languages.</td></tr><tr><td colspan="1" rowspan="1">e</td><td colspan="3" rowspan="1">The data manager selects the new default language.</td></tr><tr><td colspan="1" rowspan="1">f</td><td colspan="3" rowspan="1">The system saves the new default language in its configuration.</td></tr><tr><td colspan="1" rowspan="1">g</td><td colspan="3" rowspan="1">The system records an audit log entry.</td></tr><tr><td colspan="1" rowspan="1">h</td><td colspan="3" rowspan="1">The system informs the security officer of the operation success.</td></tr><tr><td colspan="1" rowspan="1">g</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Alternate flows</td></tr><tr><td colspan="4" rowspan="1">Install a new alternate language</td></tr><tr><td colspan="1" rowspan="1">c1</td><td colspan="3" rowspan="1">The portal manager selects to install a new language.</td></tr><tr><td colspan="1" rowspan="1">d1</td><td colspan="3" rowspan="1">The system requests the portal manager to provide the language file.</td></tr><tr><td colspan="1" rowspan="1">e1</td><td colspan="3" rowspan="1">The portal manager selects the language file on his local computer.</td></tr><tr><td colspan="1" rowspan="1">f1</td><td colspan="3" rowspan="1">The system validates the language file.</td></tr><tr><td colspan="1" rowspan="1">g1</td><td colspan="3" rowspan="1">The file is valid. The system installs the new language from the file.</td></tr><tr><td colspan="1" rowspan="1">h1</td><td colspan="3" rowspan="1">The system records an audit log entry.</td></tr><tr><td colspan="1" rowspan="1">i1</td><td colspan="3" rowspan="1">The system informs the portal manager of the install success.</td></tr><tr><td colspan="1" rowspan="1">j1</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Uninstall an alternate language</td></tr><tr><td colspan="1" rowspan="1">c2</td><td colspan="3" rowspan="1">The data manager selects the language of interest and chooses the optionto uninstall it.</td></tr><tr><td colspan="1" rowspan="1">d2</td><td colspan="3" rowspan="1">The system uninstalls the language.</td></tr><tr><td colspan="1" rowspan="1">e2</td><td colspan="3" rowspan="1">The system records an audit log entry.</td></tr><tr><td colspan="1" rowspan="1">i2</td><td colspan="3" rowspan="1">The system informs the portal manager of the uninstall success.</td></tr><tr><td colspan="1" rowspan="1">j2</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Handle invalid language file</td></tr><tr><td colspan="1" rowspan="1">g1.1</td><td colspan="3" rowspan="1">The system informs the portal manager that it's impossible to install thelanguage because the file he provided is invalid. The use case ends.</td></tr></table>

## Front end use cases

Visitor

Send	  feedback	  to	  the	  portal	  contact	  person
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-V1 - Send feedback to the portal contact person</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The visitor sends remarks or suggestions about the portal or about thehosted data to the portal contact person.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>1</td></tr><tr><td rowspan=1 colspan=1>Preconditions</td><td rowspan=1 colspan=3>The portal manager has customized NPT instance and provided informationfor the contact person.</td></tr><tr><td rowspan=1 colspan=1>Trigger</td><td rowspan=1 colspan=3>The visitor decides to contact the NPT portal contact person.</td></tr><tr><td rowspan=1 colspan=4>Main flow</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=3>The use case starts when the visitor selects to send feedback.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=3>The system requests the visitor to enter a text and body for the messageand personal information (name and email address).</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=3>The visitor supplies that information.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=3>The system validates the email address and checks that the message bodyis not empty.</td></tr><tr><td rowspan=1 colspan=1>e</td><td rowspan=1 colspan=3>The system sends the message along with the visitor&#x27;s personal informationto the contact person by email.</td></tr><tr><td rowspan=1 colspan=1>f</td><td rowspan=1 colspan=3>The system informs the visitor that his feedback has successfully been sent.</td></tr><tr><td rowspan=1 colspan=1>g</td><td rowspan=1 colspan=3>The use case ends.</td></tr><tr><td rowspan=1 colspan=4>Alternate flows</td></tr><tr><td rowspan=1 colspan=4>Handle invalid email address</td></tr><tr><td rowspan=1 colspan=1>d1</td><td rowspan=1 colspan=3>If the email address is invalid, the system asks the visitor to enter a validemail address and prevents her to send the feedback until done. The usecase resumes to step b.</td></tr><tr><td rowspan=1 colspan=4>Handle blank message body</td></tr><tr><td rowspan=1 colspan=1>d2</td><td rowspan=1 colspan=3>If the message body is empty, the system asks the visitor to enter one. Theuse case resumes to step b.</td></tr><tr><td rowspan=1 colspan=4>Exceptions</td></tr><tr><td rowspan=1 colspan=4>Handle error during sending the email</td></tr><tr><td rowspan=1 colspan=1>e3</td><td rowspan=1 colspan=3>If an error occurs while sending the email, the system warns the user aboutthe issue, apologies and asks the user to try again later.</td></tr><tr><td rowspan=1 colspan=1>f3</td><td rowspan=1 colspan=3>The system records an error log entry.</td></tr><tr><td rowspan=1 colspan=1>g3</td><td rowspan=1 colspan=3>The use case ends.</td></tr></table>

Build	  an	  occurrence	  record	  selection	  filter

<table><tr><td colspan="1" rowspan="1">Identifier-Name</td><td colspan="1" rowspan="1">S-V1 - Build an occurrence record selection filter</td></tr><tr><td colspan="2" rowspan="1">Main flow</td></tr><tr><td colspan="1" rowspan="1">a</td><td colspan="1" rowspan="1">The sub flow starts when the selects to search for occurrence records.</td></tr><tr><td colspan="1" rowspan="1">b</td><td colspan="1" rowspan="1">The system displays the filter-building interface to the visitor.</td></tr><tr><td colspan="1" rowspan="1">C</td><td colspan="1" rowspan="1">Perform Add a criterion to the filter.</td></tr><tr><td colspan="1" rowspan="1">d</td><td colspan="1" rowspan="1">User repeats step c until the filter matches only the occurrence recordshe's interested in.</td></tr><tr><td colspan="2" rowspan="1">Alternate flow</td></tr><tr><td colspan="2" rowspan="1">Remove a criterion.</td></tr><tr><td colspan="1" rowspan="1">c1.1</td><td colspan="1" rowspan="1">Provided that the filter has at least one criterion. The visitor selects acriterion and chooses to remove it.</td></tr><tr><td colspan="1" rowspan="1">c1.2</td><td colspan="1" rowspan="1">The system removes the criterion from the filter. The use case resumes atstep d.</td></tr></table>

Add	  a	  criterion	  to	  the	  filter
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=1>S-V2 - Add a criterion to the filter</td></tr><tr><td rowspan=1 colspan=2>Main flow: Add a taxonomic criterion</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=1>The visitor selects to add a taxonomic criterion.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=1>The visitor finds the taxon of interest.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=1>The system adds the criterion to the filter.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=1>The sub flow ends.</td></tr><tr><td rowspan=1 colspan=2>Alternate flows</td></tr><tr><td rowspan=1 colspan=2>Add a depth criterion</td></tr><tr><td rowspan=1 colspan=1>a1</td><td rowspan=1 colspan=1>The visitor selects to add a depth criterion.</td></tr><tr><td rowspan=1 colspan=1>b1</td><td rowspan=1 colspan=1>The visitor enters a minimum and/or maximum observation depth value(s).The sub flow ends.</td></tr><tr><td rowspan=1 colspan=2>Add an altitude criterion</td></tr><tr><td rowspan=1 colspan=1>a2</td><td rowspan=1 colspan=1>The visitor selects to add an altitude criterion.</td></tr><tr><td rowspan=1 colspan=1>b2</td><td rowspan=1 colspan=1>The visitor enters a minimum and/or maximum observation altitudevalue(s). The sub flow ends.</td></tr><tr><td rowspan=1 colspan=2>Add a date criterion</td></tr><tr><td rowspan=1 colspan=1>a3</td><td rowspan=1 colspan=1>The visitor selects to add a date criterion</td></tr><tr><td rowspan=1 colspan=1>b3</td><td rowspan=1 colspan=1>The visitor enters a start and/or an end observation date(s). The sub flowends.</td></tr><tr><td rowspan=1 colspan=2>Add a dataset criterion</td></tr><tr><td rowspan=1 colspan=1>a4</td><td rowspan=1 colspan=1>The visitor selects to add a dataset criterion.</td></tr><tr><td rowspan=1 colspan=1>b4.1</td><td rowspan=1 colspan=1>The system retrieves the list of hosted occurrence resources and displaysthe list to the visitor.</td></tr><tr><td rowspan=1 colspan=1>b4.2</td><td rowspan=1 colspan=1>The visitor selects the occurrence resource of interest. The sub flow ends.</td></tr><tr><td rowspan=1 colspan=1>Add a basis of recor</td><td rowspan=1 colspan=1>d criterion</td></tr><tr><td rowspan=1 colspan=1>a5</td><td rowspan=1 colspan=1>The visitor selects to add a basis of records criterion.</td></tr><tr><td rowspan=1 colspan=1>b5.1</td><td rowspan=1 colspan=1>The system displays the list of basis of records to the visitor.</td></tr><tr><td rowspan=1 colspan=1>b5.2</td><td rowspan=1 colspan=1>The visitor selects the basis of record from the proposed list. The sub flowends.</td></tr><tr><td rowspan=1 colspan=1>Add a geographic ar</td><td rowspan=1 colspan=1>ea criterion</td></tr><tr><td rowspan=1 colspan=1>a6</td><td rowspan=1 colspan=1>The visitor selects to add a geographic area criterion.</td></tr><tr><td rowspan=1 colspan=1>b6</td><td rowspan=1 colspan=1>User draws a polygon defining his area of interest on a map interface. Thesub flow ends.</td></tr></table>

Select	  occurrence	  records	  and	  view	  distribution	  map

<table><tr><td>Identifier-Name Description</td><td colspan="3">UC-V2 - Select occurrence records and view distribution map</td></tr><tr><td></td><td colspan="3">The visitor wants to discover and access occurrence records. He can select</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="3" rowspan="1">his records of interest using simple taxonomic search or a more elaborateadvanced search by combining various criteria.</td></tr><tr><td colspan="1" rowspan="1">Actors</td><td colspan="3" rowspan="1">Visitor</td></tr><tr><td colspan="1" rowspan="1">Priority</td><td colspan="1" rowspan="1">5</td><td colspan="1" rowspan="1">Frequency</td><td colspan="1" rowspan="1">5</td></tr><tr><td colspan="4" rowspan="1">Main flow (search occurrence records by building a selection filter i.e. advanced search)</td></tr><tr><td colspan="1" rowspan="1">a</td><td colspan="3" rowspan="1">The use case starts when the visitor selects to search occurrences.</td></tr><tr><td colspan="1" rowspan="1">b</td><td colspan="3" rowspan="1">The system proposes the visitor two search options: taxonomic search andadvanced search.</td></tr><tr><td colspan="1" rowspan="1">C</td><td colspan="3" rowspan="1">The visitor selects to search occurrence records using advanced search.</td></tr><tr><td colspan="1" rowspan="1">d</td><td colspan="3" rowspan="1">Perform Build an occurrence record selection filter.</td></tr><tr><td colspan="1" rowspan="1">e</td><td colspan="3" rowspan="1">The visitor launches the search.</td></tr><tr><td colspan="1" rowspan="1">f</td><td colspan="3" rowspan="1">The system retrieves the occurrence records matching the filter criteria.</td></tr><tr><td colspan="1" rowspan="1">g</td><td colspan="3" rowspan="1">The system records a data usage log entry with type mapped'.</td></tr><tr><td colspan="1" rowspan="1">h</td><td colspan="3" rowspan="1">The system displays the distribution map for the occurrence recordselection.</td></tr><tr><td colspan="1" rowspan="1">i</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Alternate flows</td></tr><tr><td colspan="4" rowspan="1">Search occurrence records using taxonomic search.</td></tr><tr><td colspan="1" rowspan="1">c1</td><td colspan="3" rowspan="1">The visitor selects to search occurrence records using taxonomic search.</td></tr><tr><td colspan="1" rowspan="1">d1</td><td colspan="3" rowspan="1">Perform Select a taxon.</td></tr><tr><td colspan="1" rowspan="1">e1</td><td colspan="3" rowspan="1">The visitor launches the search.</td></tr><tr><td colspan="1" rowspan="1">f1</td><td colspan="3" rowspan="1">The system retrieves the occurrence records for that taxon. Use caseresumes at step g.</td></tr><tr><td colspan="4" rowspan="1">Search occurrence records for a dataset.</td></tr><tr><td colspan="1" rowspan="1">a2</td><td colspan="3" rowspan="1">Perform Select an occurrence resource.</td></tr><tr><td colspan="1" rowspan="1">b2</td><td colspan="3" rowspan="1">The system displays the details for this occurrence resource and thedistribution map for associated occurrence records. The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Search occurrence records for a taxon using full text search.</td></tr><tr><td colspan="1" rowspan="1">a3</td><td colspan="3" rowspan="1">The visitor searches portal using full text search. If no taxon is returned, theuse case ends.</td></tr><tr><td colspan="1" rowspan="1">b3</td><td colspan="3" rowspan="1">The visitor selects a taxon.</td></tr><tr><td colspan="1" rowspan="1">d2</td><td colspan="3" rowspan="1">The system displays the details for this taxon and the distribution map forassociated occurrence records. The use case ends.</td></tr></table>

View	  occurrence	  record	  selection	  as	  a	  table
<table><tr><td colspan="1" rowspan="1">Identifier-Name</td><td colspan="3" rowspan="1">UC-V3 - View occurrence record selection as a table</td></tr><tr><td colspan="1" rowspan="1">Description</td><td colspan="3" rowspan="1">User selects to view occurrence records selection as a table in order todisplay their attributes.</td></tr><tr><td colspan="1" rowspan="1">Actors</td><td colspan="3" rowspan="1">Visitor</td></tr><tr><td colspan="1" rowspan="1">Priority</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">Frequency</td><td colspan="1" rowspan="1">3</td></tr><tr><td colspan="1" rowspan="1">Preconditions</td><td colspan="3" rowspan="1">The record selection contains at least one record.</td></tr><tr><td colspan="4" rowspan="1">Main flow</td></tr><tr><td colspan="1" rowspan="1">a</td><td colspan="3" rowspan="1">The visitor selects occurrence records and view distribution map.</td></tr><tr><td colspan="1" rowspan="1">b</td><td colspan="3" rowspan="1">The visitor chooses the option to view the occurrence record selection as atable.</td></tr><tr><td colspan="1" rowspan="1">C</td><td colspan="3" rowspan="1">The system records a data usage log entry with type ‘viewed'.</td></tr><tr><td>d</td><td colspan="3">The system retrieves the selected occurrence records and displays them as a table.</td></tr><tr><td>e</td><td colspan="3">The use case ends.</td></tr></table>

Export	  occurrence	  record	  selection
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-V4 - Export occurrence record selection</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>User exports the occurrence selection for further analysis.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>4</td></tr><tr><td rowspan=1 colspan=1>Preconditions</td><td rowspan=1 colspan=3>The record selection contains at least one record.</td></tr><tr><td rowspan=1 colspan=1>Post conditions</td><td rowspan=1 colspan=3>A file containing the record selection has been transferred to the visitor&#x27;slocal computer.</td></tr><tr><td rowspan=1 colspan=4>Main flow</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=3>The visitor selects occurrence records and views distribution map.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=3>The visitor chooses the option to download the record selection in hisformat of choice.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=3>The system checks that the user has accepted the data usage agreement.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=3>The system records a data usage log entry with type downloaded&#x27;.</td></tr><tr><td rowspan=1 colspan=1>e</td><td rowspan=1 colspan=3>The system warns visitor that the process may take up to half an hour. Itprovides visitor a download link that will allow him to retrieve the filelater.</td></tr><tr><td rowspan=1 colspan=1>f</td><td rowspan=1 colspan=3>The system builds the file.</td></tr><tr><td rowspan=1 colspan=1>g</td><td rowspan=1 colspan=3>The visitor later follows the download link.</td></tr><tr><td rowspan=1 colspan=1>h</td><td rowspan=1 colspan=3>The file is ready for download. The system informs the visitor that thebuilding process has been successfully carried out and offers an option todownload the file.</td></tr><tr><td rowspan=1 colspan=1>i</td><td rowspan=1 colspan=3>The visitor chooses to download the file.</td></tr><tr><td rowspan=1 colspan=1>j</td><td rowspan=1 colspan=3>The system transfers the file to the visitor&#x27;s local computer.</td></tr><tr><td rowspan=1 colspan=1>k</td><td rowspan=1 colspan=3>The use case ends.</td></tr><tr><td rowspan=1 colspan=4>Alternate flows</td></tr><tr><td rowspan=1 colspan=4>The data usage agreement hasn&#x27;t been accepted by the visitor</td></tr><tr><td rowspan=1 colspan=1>C1</td><td rowspan=1 colspan=3>If the visitor has not accepted the data usage agreement, the systemdisplays it to the user and prompts the user to accept it. If the user does,the system will remember and the use case resumes at step c. If he doesn&#x27;t,the use case ends.</td></tr><tr><td rowspan=1 colspan=4>The file is not finished building yet</td></tr><tr><td rowspan=1 colspan=1>h2</td><td rowspan=1 colspan=3>The system informs the visitor that the export process is not finished yetand suggests him to try again in a few moments. Use case returns to step f.</td></tr></table>

Export	  distribution	  map	  as	  an	  image
<table><tr><td colspan="1" rowspan="1">Identifier-Name</td><td colspan="3" rowspan="1">UC-V5 - Export distribution map as an image</td></tr><tr><td colspan="1" rowspan="1">Description</td><td colspan="3" rowspan="1">The visitor exports distribution map as an image so as to be able, e.g., toinsert it in a paper.</td></tr><tr><td colspan="1" rowspan="1">Actors</td><td colspan="3" rowspan="1">Visitor</td></tr><tr><td colspan="1" rowspan="1">Priority</td><td colspan="1" rowspan="1">3</td><td colspan="1" rowspan="1">Frequency</td><td colspan="1" rowspan="1">4</td></tr><tr><td colspan="1" rowspan="1">Post conditions</td><td colspan="3" rowspan="1">An image of the distribution map has been transferred to the visitor's local</td></tr><tr><td colspan="1" rowspan="1"></td><td colspan="3" rowspan="1">computer.</td></tr><tr><td colspan="4" rowspan="1">Main flow</td></tr><tr><td colspan="1" rowspan="1">a</td><td colspan="3" rowspan="1">The visitor selects and accesses occurrence records.</td></tr><tr><td colspan="1" rowspan="1">b</td><td colspan="3" rowspan="1">The visitor chooses the option to export the distribution map as an image.</td></tr><tr><td colspan="1" rowspan="1">C</td><td colspan="3" rowspan="1">The system transfers an image file of the distribution map to the visitor'slocal computer.</td></tr><tr><td colspan="1" rowspan="1">d</td><td colspan="3" rowspan="1">The use case ends.</td></tr></table>

Search	  portal	  using	  full	  text	  search
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-V6 - Search portal using full text search</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The visitor searches resource metadata, blog, article and news entries usingfull text search in order to find and access matching resources and entries.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>4</td></tr><tr><td rowspan=1 colspan=4>Main flow</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=3>The use case starts when the visitor selects to search the portal using fulltext search.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=3>The system prompts visitor to type his keyword query.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=3>The visitor enters the query.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=3>The system retrieves the list of matching resources and entries. The systemdisplays the those results grouped by data types with an option to view thedetails for each of them.</td></tr><tr><td rowspan=1 colspan=1>e</td><td rowspan=1 colspan=3>The use case ends.</td></tr></table>

Contact	  an	  occurrence	  resource	  publisher
<table><tr><td colspan="1" rowspan="1">Identifier-Name</td><td colspan="3" rowspan="1">UC-V7 - Contact an occurrence resource publisher</td></tr><tr><td colspan="1" rowspan="1">Description</td><td colspan="3" rowspan="1">The visitor contacts the publisher of an occurrence resource to requestmore information or send a comment.</td></tr><tr><td colspan="1" rowspan="1">Actors</td><td colspan="3" rowspan="1">Visitor</td></tr><tr><td colspan="1" rowspan="1">Priority</td><td colspan="1" rowspan="1">2</td><td colspan="1" rowspan="1">Frequency</td><td colspan="1" rowspan="1">1</td></tr><tr><td colspan="1" rowspan="1">Precondition</td><td colspan="3" rowspan="1">The dataset provider's metadata contains a valid contact email address.</td></tr><tr><td colspan="1" rowspan="1">Post conditions</td><td colspan="3" rowspan="1">The visitor's message has been sent to the provider's contact email address.</td></tr><tr><td colspan="1" rowspan="1">Main flow</td><td colspan="3" rowspan="1"></td></tr><tr><td colspan="1" rowspan="1">a</td><td colspan="3" rowspan="1">Perform Select an occurrence resource.</td></tr><tr><td colspan="1" rowspan="1">b</td><td colspan="3" rowspan="1">The visitor selects to contact the data provider of this dataset.</td></tr><tr><td colspan="1" rowspan="1">C</td><td colspan="3" rowspan="1">The system requests the visitor to enter the subject and body of themessage and personal information (name and email address).</td></tr><tr><td colspan="1" rowspan="1">d</td><td colspan="3" rowspan="1">The visitor enters the requested information.</td></tr><tr><td colspan="1" rowspan="1">e</td><td colspan="3" rowspan="1">The system validates the email address and checks that the message body isnot empty.</td></tr><tr><td colspan="1" rowspan="1">f</td><td colspan="3" rowspan="1">The system sends the visitor's message and personal information to thedataset provider by email. The system informs the visitor that the messagehas successfully been sent.</td></tr><tr><td colspan="1" rowspan="1">g</td><td colspan="3" rowspan="1">The use case ends.</td></tr><tr><td colspan="4" rowspan="1">Alternate flows</td></tr><tr><td colspan="4" rowspan="1">Handle invalid email address</td></tr><tr><td colspan="1" rowspan="1">e2</td><td colspan="3" rowspan="1">The system informs the visitor that the email address he provided isinvalid. Use case resumes at step c.</td></tr><tr><td colspan="4" rowspan="1">Handle blank message body</td></tr><tr><td colspan="1" rowspan="1">e3</td><td colspan="3" rowspan="1">The system informs the visitor that the message body cannot be left blank.The use case resumes at step c.</td></tr><tr><td colspan="4" rowspan="1">Exception</td></tr><tr><td colspan="4" rowspan="1">Handle error sending the email</td></tr><tr><td colspan="1" rowspan="1">f4</td><td colspan="3" rowspan="1">If an error occurs while sending the email, the system warns the user thatthe message could not be sent, apologies for the inconvenience andsuggests the visitor to try again later.</td></tr><tr><td colspan="1" rowspan="1">g4</td><td colspan="3" rowspan="1">The system records an error log entry.</td></tr><tr><td colspan="1" rowspan="1">h4</td><td colspan="3" rowspan="1">The use case ends.</td></tr></table>

Export	  a	  checklist
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-V8 - Export a checklist</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The visitor downloads a checklist for local consultation/analysis.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>3</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr><tr><td rowspan=1 colspan=4>Main flow</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=3>The use case starts when the visitor chooses the option to view the list ofchecklists hosted on the portal.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=3>The system retrieves the list of checklist resources and displays it to thevisitor.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=3>The visitor selects the checklist resource of interest and chooses the optionto view its details.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=3>The system displays detailed metadata for this checklist resource and anexport checklist option.</td></tr><tr><td rowspan=1 colspan=1>e</td><td rowspan=1 colspan=3>The visitor selects to export the checklist.</td></tr><tr><td rowspan=1 colspan=1>f</td><td rowspan=1 colspan=3>The system transfers the archived checklist resource file to the visitor&#x27;slocal computer.</td></tr><tr><td rowspan=1 colspan=1>g</td><td rowspan=1 colspan=3>The use case ends.</td></tr></table>

Select	  a	  taxon
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=1>S-V3 - Select a taxon</td></tr><tr><td rowspan=1 colspan=2>Main flow</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=1>The visitor chooses the option to find a taxon.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=1>The system presents a taxonomic tree and a taxon search interface.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=1>The visitor browses the tree until he finds the taxon he&#x27;s interested in.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=1>The visitor selects this taxon.</td></tr><tr><td rowspan=1 colspan=2>Alternative flow</td></tr><tr><td rowspan=1 colspan=2>Selects taxon by searching by name</td></tr><tr><td rowspan=1 colspan=1>c1.1</td><td rowspan=1 colspan=1>The visitor searches the taxon by name (scientific or common). The visitorenters part of the name.</td></tr><tr><td rowspan=1 colspan=1>c1.2</td><td rowspan=1 colspan=1>The system presents the list of matching taxa. The use case resumes at stepd.</td></tr></table>

Select	  an	  occurrence	  resource
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=1>S-V4 - Select an occurrence resource</td></tr><tr><td rowspan=1 colspan=2>Main flow</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=1>The visitor selects to list datasets.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=1>The system retrieves the list of occurrence resources. The system displaysthe list to the visitor.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=1>The visitor selects the occurrence resource of interest.</td></tr><tr><td rowspan=1 colspan=2>Alternate flows</td></tr><tr><td rowspan=1 colspan=1>a1</td><td rowspan=1 colspan=1>The visitor searches portal using full text search. If at least one occurrenceresource is returned, the flow resumes to step c. If not, it ends.</td></tr></table>

Choose	  portal	  language

<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-V9 - Choose portal language</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The visitor chooses his language of preference.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>5</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr><tr><td rowspan=1 colspan=1>Preconditions</td><td rowspan=1 colspan=3>The portal manager has configured front office languages with at least onealternate language.</td></tr><tr><td rowspan=1 colspan=1>Post conditions</td><td rowspan=1 colspan=3>The portal uses the chosen language for that visitor from now on.</td></tr><tr><td rowspan=1 colspan=4>Main flow</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=3>The use case starts when the visitor selects to choose portal language.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=3>The system retrieves the list of available languages to the visitor.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=3>The system displays the list to the visitor.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=3>The visitor chooses his preferred language.</td></tr><tr><td rowspan=1 colspan=1>e</td><td rowspan=1 colspan=3>The system switches portal language to the chosen language.</td></tr><tr><td rowspan=1 colspan=1>f</td><td rowspan=1 colspan=3>The use case ends.</td></tr></table>

## Registered	  visitor

A visitor may only initiate the use cases in this section if he is logged into the system as a registered visitor.

Save	  a custom	  filter

<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-RV1 - Save a custom filter</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The registered visitor builds an occurrence record filter and wants to beable to reuse it in the future. To do so, he saves the filter in his profile.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Registered visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr><tr><td rowspan=1 colspan=4>Main flow</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=3>Perform Build an occurrence record selection filter.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=3>Visitor selects to save the current filter.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=3>The system prompts visitor for a name and description for the filter.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=3>The visitor enters a name and description for the filter.</td></tr><tr><td rowspan=1 colspan=1>e</td><td rowspan=1 colspan=3>The system saves the filter in the registered visitor&#x27;s profile.</td></tr><tr><td rowspan=1 colspan=1>f</td><td rowspan=1 colspan=3>The use case ends.</td></tr></table>

Load	  a	  custom	  filter
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-RV2 - Load a custom filter</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The registered visitor loads a filter he previously saved in his profile.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Registered visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr><tr><td rowspan=1 colspan=1>Preconditions</td><td rowspan=1 colspan=3>The registered visitor is displayed the filter building interface.The registered visitor has saved at least one filter.</td></tr><tr><td rowspan=1 colspan=4>Main flow</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=3>The use case starts when the visitor selects to manage custom filters.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=3>The system retrieves the list of filters for the registered visitor. The systemdisplays the list to the visitor with options to load or delete each of them.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=3>The visitor selects the filter of interest and chooses the option to load it.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=3>The system retrieves the filter criteria and populates the filter-buildinginterface with these criteria.</td></tr><tr><td rowspan=1 colspan=1>e</td><td rowspan=1 colspan=3>The use case ends.</td></tr></table>

Delete	  a	  custom	  filter
<table><tr><td rowspan=1 colspan=1>Identifier-Name</td><td rowspan=1 colspan=3>UC-RV3 - Delete a custom filter</td></tr><tr><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=3>The visitor wants to delete a previously saved filter.</td></tr><tr><td rowspan=1 colspan=1>Actors</td><td rowspan=1 colspan=3>Registered visitor</td></tr><tr><td rowspan=1 colspan=1>Priority</td><td rowspan=1 colspan=1>1</td><td rowspan=1 colspan=1>Frequency</td><td rowspan=1 colspan=1>2</td></tr><tr><td rowspan=1 colspan=1>Preconditions</td><td rowspan=1 colspan=3>The visitor is displayed the filter building interface.The visitor has saved at least one filter.</td></tr><tr><td rowspan=1 colspan=4>Main flow</td></tr><tr><td rowspan=1 colspan=1>a</td><td rowspan=1 colspan=3>The use case starts when the visitor selects to manage custom filters.</td></tr><tr><td rowspan=1 colspan=1>b</td><td rowspan=1 colspan=3>The system retrieves the list of filters for the registered visitor. The systemdisplays the list to the visitor with options to load or delete each of them.</td></tr><tr><td rowspan=1 colspan=1>C</td><td rowspan=1 colspan=3>The visitor selects the filter of interest and chooses the option to delete it.</td></tr><tr><td rowspan=1 colspan=1>d</td><td rowspan=1 colspan=3>The system deletes the filter and informs the registered visitor of thedeletion success.</td></tr><tr><td rowspan=1 colspan=1>e</td><td rowspan=1 colspan=3>The use case ends.</td></tr></table>

Business rules
<table><tr><td>BR ID</td><td>Name</td></tr><tr><td>BR1</td><td>Visitors must accept the portal data usage agreement before being allowed to export data from the portal.</td></tr><tr><td>BR2</td><td>To avoid conflict, the data usage agreement for all NPT instances is the same as on GBIF portal.</td></tr><tr><td>BR3</td><td>Only user logged into the system using an account with an administrator role can manage user accounts. Only user logged into the system using an account with a data manager role can</td></tr><tr><td>BR4</td><td>access the following functionalities: manage resources, manage data sources, manage harvesting jobs, and manage taxonomic backbone. Only user logged into the system using an account with a portal manager role</td></tr><tr><td>BR5</td><td>can access the following functionalities: manage blog posts, pages and news entries, customize NPT instance and choose languages available on the front end.</td></tr><tr><td>BR6</td><td>Only user logged into the system using an account with an administrator role can configure the distribution map, manage installed modules and manage user accounts.</td></tr><tr><td>BR7</td><td>Only user logged into the system using an account with a portal manager, administrator or data manager role can access data metrics with a visibility status of hidden’.</td></tr></table>

## References

NPT resources for further information can be found on:

NPT group on GBIF Community site: http://community.gbif.org/pg/groups/3507/nodes-portal-toolkit-npt/

## Standards, formats, tools and API documentation:

Audubon: http://www.keytonature.eu/wiki/Audubon\_Core

EML:http://knb.ecoinformatics.org/software/eml/eml-2.0.1/index.html

Darwin core: http://rs.tdwg.org/dwc/

Darwin core archive: http://www.gbif.org/informatics/standards-andtools/publishing-data/data-standards/darwin-core-archives/

Documentation on the GBIF Portal API Google Code site: http://code.google.com/p/gbif-portalapi/

The GBIF Integrated Publishing Toolkit User Manual: http://code.google.com/p/gbif-providertoolkit/wiki/IPT2ManualNotes

Integrated Publishing Toolkit (IPT) - Architectural view:   
http://code.google.com/p/gbif-providertoolkit/downloads/detail?name=ipt  
architecture\_1.1.pdf