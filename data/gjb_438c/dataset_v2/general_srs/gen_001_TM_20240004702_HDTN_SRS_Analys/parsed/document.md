# High-Rate Delay Tolerant Networking (HDTN) Software Requirements Analysis

Rachel Dudukovich, Jose Lombay-Gonzalez, Stephanie Booth, Ethan Schweinsberg,   
Joseph Ponyik, Brian Tomko, and Nadia Kortas   
Glenn Research Center, Cleveland, Ohio

Eric Brace HX5, LLC, Brook Park, Ohio

Daniel Raible, Amber Waid, Alyssa Brewer, and Shira Nadile Glenn Research Center, Cleveland, Ohio

Since its founding, NASA has been dedicated to the advancement of aeronautics and space science. The NASA scientifi c and technical information (STI) program plays a key part in helping NASA maintain this important role.

The NASA STI program operates under the auspices of the Agency Chief Information Ofi cer. It collects, organizes, provides for archiving, and disseminates NASA’s STI. The NASA STI program provides access to the NTRS Registered and its public interface, the NASA Technical Reports Server, thus providing one of the largest collections of aeronautical and space science STI in the world. Results are published in both non-NASA channels and by NASA in the NASA STI Report Series, which includes the following report types:

## • TECHNICAL PUBLICATION.

Reports of completed research or a major signifi cant phase of research that present the results of NASA Programs and include extensive data or theoretical analysis. Includes compilations of signifi cant scientifi c and technical data and information deemed to be of continuing reference value. NASA counterpart of peer-reviewed formal professional papers but has less stringent limitations on manuscript length and extent of graphic presentations.

## • TECHNICAL MEMORANDUM.

Scientifi c and technical fi ndings that are preliminary or of specialized interest, e.g., quick release reports, working papers, and bibliographies that contain minimal annotation. Does not contain extensive analysis.

• CONTRACTOR REPORT. Scientifi c and technical fi ndings by NASAsponsored contractors and grantees.

CONTRACTOR REPORT. Scientifi c and technical fi ndings by NASAsponsored contractors and grantees.

CONFERENCE PUBLICATION. Collected papers from scientifi c and technical conferences, symposia, seminars, or other meetings sponsored or co-sponsored by NASA.

## • SPECIAL PUBLICATION.

Scientifi c, technical, or historical information from NASA programs, projects, and missions, often concerned with subjects having substantial public interest.

## • TECHNICAL TRANSLATION.

English-language translations of foreign scientifi c and technical material pertinent to NASA’s mission.

Specialized services also include organizing and publishing research results, distributing specialized research announcements and feeds, providing information desk and personal search support, and enabling data exchange services.

For more information about the NASA STI program, see the following:

• Access the NASA STI program home page at http://www.sti.nasa.gov

# High-Rate Delay Tolerant Networking (HDTN) Software Requirements Analysis

Rachel Dudukovich, Jose Lombay-Gonzalez, Stephanie Booth, Ethan Schweinsberg,   
Joseph Ponyik, Brian Tomko, and Nadia Kortas   
Glenn Research Center, Cleveland, Ohio

Eric Brace HX5, LLC, Brook Park, Ohio

Daniel Raible, Amber Waid, Alyssa Brewer, and Shira Nadile Glenn Research Center, Cleveland, Ohio

National Aeronautics and Space Administration

## Acknowledgments

The authors would like to thank the NASA Space Communications and Navigation (SCaN) program and the Delay Tolerant Networking (DTN) project for supporting this work, and in particular the continual guidance and management provided by John Nowakowski is most appreciated.

![](images/602bca8987f334157749662e16c79837fb5612606421659ff9b092a8dfe335f2.jpg)  
Level of Review: This material has been technically reviewed by technical management.

This report is available in electronic form at https://www.sti.nasa.gov/ and https://ntrs.nasa.gov/

## CONTENTS

Preface..   
Introduction 1   
Reference Documents . . 2   
1 BPv6 Requirements .. 3   
2 BPv7 Requirements . .28   
3 BPSec Requirements. .41   
4 Routing Requirements .61   
5 TCPCL Requirements. .. 63   
6 STCP Requirements .. 81   
7 UDP Requirements . .. 83   
8 LTP Requirements .. .. 85   
Appendix A.—Abbreviations .99   
Appendix B.—Revision History ... .101

## PREFACE

Space Communications and Navigation (SCaN) is developing new communications technologies to increase the amount of science data returned on future space missions. The High-Rate Delay Tolerant Networking (HDTN) project at NASA Glenn Research Center (GRC) will provide reliable internetworking as a high-speed path for moving data between spacecraft payloads, and across communication systems that operate on a range of different rates.

This document captures a subset of preliminary software requirements for the HDTN Computer Software Configuration Item (CSCI).

# High-Rate Delay Tolerant Networking (HDTN) Software Requirements Analysis

Rachel Dudukovich, Jose Lombay-Gonzalez, Stephanie Booth, Ethan Schweinsberg, Joseph Ponyik, Brian Tomko, and Nadia Kortas National Aeronautics and Space Administration Glenn Research Center Cleveland, Ohio 44135

Eric Brace HX5, LLC Brook Park, Ohio 44142

Daniel Raible, Amber Waid, Alyssa Brewer, and Shira Nadile National Aeronautics and Space Administration Glenn Research Center Cleveland, Ohio 44135

## INTRODUCTION

This document serves as a detailed analysis of the main networking protocols implemented by HDTN. Sources of the protocol specifications include Internet Engineering Task Force (IETF) Request for Comments (RFC) and Consultative Committee for Space Data Systems (CCSDS) standards. The focus of this report is to derive software requirements suitable for NASA Procedural Requirements 7150.2D Class B compliance, including requirements traceability and software verification and validation, from the source specifications. This analysis will be incorporated into the finalized HDTN Software Requirements Specification (SRS) but does not encompass the full scope of the HDTN SRS. Requirements in this document are considered draft. The complete requirements will include bundle application requirements, interface requirements, computer resource requirements, software quality factors, and additional requirements as determined by the project. This document is publicly released to the greater community to receive feedback and foster collaboration opportunities.

## Scope

Candidate requirements outlined in this document include bundle layer requirements, security requirements, convergence layer requirements and routing requirements. Formalized requirement levels are not captured in this document. Service level and network level requirements are out of the scope of this document.

## Terminology

Requirement statements have been written using the word “shall” to indicate a planned process that must be implemented and verified. Original source documents include terms “must”, “must not”, “should”, “should not”, “may”, “required”, “shall”, and “recommended” as described in RFC 2119. In this document, “must”, “required”, and “shall” have been simplified to use only the term “shall”. Negative statements such as “shall not” have been rewritten as “shall”. These changes have been suggested per NASA software engineering best practices.

## Methodology

Source RFC documents have been analyzed for all statements containing “shall”, “shall not”, “must”, “must not”, and “required”. These statements were considered candidate software requirements. Candidate software requirements were assessed according to the content of the statement and characterized as either “Requirement”, “Design Document”, “Data Dictionary”, “Requirement and Design Document”, or “Requirement and Data Dictionary”. Statements classified as “Requirement” describe functionality that must be implemented and verified. Statements classified as “Design Document” indicate information from the source documents that describe how a feature might be implemented, sections which describe procedures, or internal software mechanisms. Statements classified as “Data Dictionary” describe information regarding packet and field formats, initial value conditions, tables of values, and other information relevant to data types used in the implementation. Statements classified as “Data Dictionary” or “Design Document” information are out of the scope of this document but may be released in future documents. Requirements derived from RFCs were cross-referenced with requirements from the related CCSDS specifications when available.

## REFERENCE DOCUMENTS

The following documents are referenced or provide guidance for this work.

## NASA Process Documents

<table><tr><td rowspan=1 colspan=1>Document Number</td><td rowspan=1 colspan=1>Document Title</td><td rowspan=1 colspan=1>Release Date</td></tr><tr><td rowspan=1 colspan=1>NPR 7150.2D</td><td rowspan=1 colspan=1>NASA Software Engineering Requirements</td><td rowspan=1 colspan=1>3/8/2022</td></tr><tr><td rowspan=1 colspan=1>NASA-HDBK-2203B</td><td rowspan=1 colspan=1>NASA Software Engineering and AssuranceHandbook, Version B</td><td rowspan=1 colspan=1>4/20/2022</td></tr><tr><td rowspan=1 colspan=1>HDTN-PLAN-004</td><td rowspan=1 colspan=1>Software Configuration Management Plan</td><td rowspan=1 colspan=1>1/18/2024</td></tr><tr><td rowspan=1 colspan=1>HDTN-PLAN-002</td><td rowspan=1 colspan=1>Project Configuration Data Management Plan</td><td rowspan=1 colspan=1>11/8/2023</td></tr><tr><td rowspan=1 colspan=1>HDTN-PLAN-006</td><td rowspan=1 colspan=1>Software Assurance and Safety Plan</td><td rowspan=1 colspan=1>1/17/2024</td></tr><tr><td rowspan=1 colspan=1>HDTN-PLAN-007</td><td rowspan=1 colspan=1>HDTN NPR 7150.2D Compliance Matrix</td><td rowspan=1 colspan=1>5/2/2024</td></tr><tr><td rowspan=1 colspan=1>GRC-SW-7150.12</td><td rowspan=1 colspan=1>Formal Inspection and Peer Review</td><td rowspan=1 colspan=1></td></tr></table>

## Protocol Specifications

<table><tr><td rowspan=1 colspan=1>Document Number</td><td rowspan=1 colspan=1>Document Title</td><td rowspan=1 colspan=1>Release Date</td></tr><tr><td rowspan=1 colspan=1>RFC 5050</td><td rowspan=1 colspan=1>Bundle Protocol Version 6</td><td rowspan=1 colspan=1>11/2007</td></tr><tr><td rowspan=1 colspan=1>CCSDS 734.2-B-1</td><td rowspan=1 colspan=1>CCSDS Bundle Protocol Specification</td><td rowspan=1 colspan=1>9/2015</td></tr><tr><td rowspan=1 colspan=1>RFC 9171</td><td rowspan=1 colspan=1>Bundle Protocol Version 7</td><td rowspan=1 colspan=1>12/14/2022</td></tr><tr><td rowspan=1 colspan=1>CCSDS 734.2-P-1.1</td><td rowspan=1 colspan=1>CCSDS Bundle Protocol Specification</td><td rowspan=1 colspan=1>4/2023</td></tr><tr><td rowspan=1 colspan=1>RFC 9172</td><td rowspan=1 colspan=1>Bundle Protocol Security (BPSec)</td><td rowspan=1 colspan=1>10/11/2023</td></tr><tr><td rowspan=1 colspan=1>RFC 9173</td><td rowspan=1 colspan=1>Default Security Contexts for Bundle Protocol Security(BPSec)</td><td rowspan=1 colspan=1>6/21/2022</td></tr><tr><td rowspan=1 colspan=1>CCSDS 734.5-R-2</td><td rowspan=1 colspan=1>CCSDS Bundle Protocol Security Specification</td><td rowspan=1 colspan=1>9/2023</td></tr><tr><td rowspan=1 colspan=1>RFC 5326</td><td rowspan=1 colspan=1>Licklider Transmission Protocol</td><td rowspan=1 colspan=1>12/8/2022</td></tr><tr><td rowspan=1 colspan=1>CCSDS 734.1-B-1</td><td rowspan=1 colspan=1>Licklider Transmission Protocol (LTP) for CCSDS</td><td rowspan=1 colspan=1>5/2015</td></tr><tr><td rowspan=1 colspan=1>RFC 9174</td><td rowspan=1 colspan=1>DTN TCP Convergence-Layer Protocol Version 4</td><td rowspan=1 colspan=1>1/31/2022</td></tr><tr><td rowspan=1 colspan=1>RFC 7122</td><td rowspan=1 colspan=1>Datagram Convergence Layers for DTN BundleProtocol and Licklider Transmission Protocol</td><td rowspan=1 colspan=1>3/2014</td></tr><tr><td rowspan=1 colspan=1>draft-burleigh-dtnrg-cgr-01</td><td rowspan=1 colspan=1>Contact Graph Routing</td><td rowspan=1 colspan=1>7/8/2010</td></tr><tr><td rowspan=1 colspan=1>CCSDS 734.3-B-1</td><td rowspan=1 colspan=1>Schedule-Aware Bundle Routing</td><td rowspan=1 colspan=1>7/2019</td></tr><tr><td rowspan=1 colspan=1>RFC 2119</td><td rowspan=1 colspan=1>Key words for use in RFCs to Indicate RequirementLevels</td><td rowspan=1 colspan=1>3/1997</td></tr></table>

## 1 BPV6 REQUIREMENTS

## BPv6-001 URI Scheme Specific Part

The Scheme Specific Part of every URI formed within the "ipn" scheme shall comprise:

1. The node number of the URI.

2. An ASCII period ('.') character.

3. The service number of the URI.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The scheme specific part is defined in RFC 6260 section 2.1. Followingthe same format between bundles will aide in consistency within thenetwork.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle from BPGen, BPSendFile, and HDTN and is shown tocontain URI&#x27;s that follow the specified &quot;ipn&quot; scheme.</td></tr></table>

## BPv6-002 CBHE Unit

A compressed primary block shall contain integers for its fields.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The CBHE-compressed primary block is defined in RFC 6260 section 2.2.If the value is at the null endpoint then that piece of the primary block iszero.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when an inspection of the codeshows that, when compressing a bundle, the primary block fields areintegers.</td></tr></table>

## BPv6-003 CBHE Encoding of EIDs by CLAs

A compressed primary block shall, in order, contain:

1. The node number of the destination endpoint ID.

2. The service number of the destination endpoint ID.

3. The node number of the source endpoint ID.

4. The service number of the source endpoint ID.

5. The node number of the report-to-endpoint ID.

6. The service number of the report-to-endpoint ID.

7. The node number of the current custodian endpoint ID.

8. The service number of the current custodian endpoint ID.

<table><tr><td colspan="1" rowspan="1">Status:</td><td colspan="1" rowspan="1">Vetted</td></tr><tr><td colspan="1" rowspan="1">Source:</td><td colspan="1" rowspan="1">CCSDS 734.2-B-1 Table A6</td></tr><tr><td colspan="1" rowspan="1">Rationale:</td><td colspan="1" rowspan="1">The CBHE-compressed primary block is defined in RFC 6260 section 2.2.If the value is at the null endpoint then that piece of the primary block iszero.</td></tr><tr><td>Verification Method:</td><td></td></tr><tr><td>Verification Approach:</td><td>This requirement will be considered verified when a test is performed that receives a bundle from BPGen, BPSendFile, and HDTN and confirms the compressed primary block contains each field in the specified order.</td></tr></table>

## BPv6-004 BP Time

DTN time shall consist of nanosecond precision since the start of the year 2000.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>BP Time is defined in CCSDS 734.2-B-1 section 3.4 as well as RFC 5050section 6.1. Time must be in the proper format down to the nanoseconds.If the node&#x27;s time system does not provide sufficient precision then theprecision of the onboard system can be used.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle from BPGen, BPSendFile, and HDTN and confirmsDTN time within the bundle consists of the number of seconds since thestart of the year 2000 down to the number of nanoseconds since the startof the indicated second.</td></tr></table>

## BPv6-005 LTP Bundle Encapsulation

When utilizing LTP bundles, the bundle shall be entirely contained in a single LTP session of reddata.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>LTP transmission is defined in CCSDS 734.2-B-1 section B3.1.2.2. Forreliable bundle transmission, bundles are encapsulated in LTP blockscontaining only red-part (reliable) data in either of these two differentencapsulations. Reliable transmission is a key component in a network.LTP blocks are organized according to the Client Operations section 7 ofthe LTP-for CCSDS Book.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when LTP bundles are shown tobe encapsulated as a LTP single bundle block without leading and trailingbytes when the bundle is to be a single LTP bundle.</td></tr></table>

## BPv6-006 Single LTP Bundle Encapsulation

When single bundle per LTP block is selected, bundles shall be encapsulated as a single bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>LTP CL adaptor is detailed in section B3.1.2.2 in CCSDS 734.2-B-1. AnLTP bundle block utilizes the Destination LTP Client Service ID for&#x27;Bundle Protocol&#x27; as specified in the SANA LTP Client Service ID NumberRegistry (reference [5]).</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when the LTP block isencapsulated as a single bundle when the bundle is to be a single LTPbundle.</td></tr></table>

## BPv6-007 UDP CL Adaptor

When using the convergence layer, UDP, encapsulated bundles shall be in UDP datagrams.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>UDP convergence layer adapter is defined in CCSDS 734.2-B-1 sectionB4; ensures network cohesion.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle from BPGen, BPSendFile, and HDTN via the UDPconvergence layer and confirms the bundle contains a single UDPdatagram with a checksum and the specified UDP port is utilized.</td></tr></table>

## BPv6-008 BP Initialization Registration Service

The Bundle Protocol services shall initiate a registration (registering a node in an endpoint) when requested.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Services at the user interface is defined in CCSDS 734.2-B-1 section4.1.1. Bringing the capability to the user is imperative for adding andsubtracting data to and from the network.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when users can create aregistration.</td></tr></table>

## BPv6-009 BP Terminate Registration Service

The Bundle Protocol services shall initiate termination of a registration when requested.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Services at the user interface is defined in CCSDS 734.2-B-1 section4.1.1. Bringing the capability to the user is imperative for adding andsubtracting data to and from the network.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when users can terminate aregistration.</td></tr></table>

## BPv6-010 BP Transmit Bundle Service

The Bundle Protocol services shall transmit a bundle to an identified bundle endpoint when requested.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Services at the user interface is defined in CCSDS 734.2-B-1 section4.1.1. Bringing the capability to the user is imperative for adding andsubtracting data to and from the network.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when users can transmit a bundle.</td></tr></table>

## BPv6-011 BP Cancel Transmission Service

The Bundle Protocol services shall initiate cancelation of a transmission when requested.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Services at the user interface is defined in CCSDS 734.2-B-1 section4.1.1. Bringing the capability to the user is imperative for adding andsubtracting data to and from the network.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when users can cancel atransmission.</td></tr></table>

## BPv6-012 BP Deliver Received Bundle Service

The Bundle Protocol services shall initiate delivery of a received bundle when requested.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Services at the user interface is defined in CCSDS 734.2-B-1 section4.1.1. Bringing the capability to the user is imperative for adding andsubtracting data to and from the network.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when users can initiate delivery ofa received bundle.</td></tr></table>

## BPv6-013 BP Bundle Structure

Bundles shall utilize SDNV encoding.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>To understand the header and data within the network, encoding needs tobe decided upon. SDNV is the encoding for bundle fields for BP v6.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle from BPGen, BPSendFile, and HDTN and confirms thebundle is encapsulated with valid SDNV encoding.</td></tr></table>

## BPv6-014 BP Bundle Block Structure

Bundles shall be a concatenated sequence of two or more block structures.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Every bundle needs at least a payload block and a primary block per RFC5050. A bundle can have additional block per requests.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when an initiated bundle containstwo or more concatenated block structures.</td></tr></table>

## BPv6-015 Primary Bundle Location

The first block in the bundle shall be the primary bundle block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The location of the primary bundle block is defined in RFC 5050 section 4.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when an initiated bundle containsa primary bundle block in the first block of the bundle.</td></tr></table>

## BPv6-016 Number of Primary Blocks

A bundle shall have one primary bundle block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Number of primary bundle blocks is defined in RFC 5050 section 4. Allmain and required header information is placed in the primary bundleblock. Therefore, having more would be redundant.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a bundle is analyzed to haveonly one primary bundle block.</td></tr></table>

## BPv6-017 Last Block Flag

The last block in the sequence shall have the "last block" flag (in its block processing control flags) set to 1.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The &quot;last block&quot; flag is defined in RFC 5050 section 4. Setting this flagshows that the data stream is ending at the block. Therefore, this flagshall be set to zero for every block in the bundle after the primary blockexcept the final block, which must be set to zero.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a bundle is analyzed withthe last block in the sequence to have the &quot;last block&quot; flags set to 1.</td></tr></table>

## BPv6-018 Custody Transfer Request Flag of an Administrative Record

The custody transfer requested flag shall be zero when the bundle is an administrative record.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 4.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle processing control flags are defined in RFC 5050 section 4.2.Network management is necessary for determining the health andstatistics of the network.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives an administrative record bundle from HDTN and confirms thebundle has the custody transfer requested flag set to zero.</td></tr></table>

## BPv6-019 Status Report Request Flag of an Administrative Record

Status report request flags shall be zero when the bundle is an administrative record.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 4.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle processing control flags are defined in RFC 5050 section 4.2.Network management is necessary for determining the health andstatistics of the network</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a receivedadministrative record bundle has all status report request flags set to zero.</td></tr></table>

## BPv6-020 Disable Identity of Bundle Protocol Features

When the bundle’s source endpoint ID is “dtn:none”, then bundle identity shall be disabled by setting its bundle protocol features:

1.The bundle's custody transfer requested flag is set to zero,

2.The "Bundle must not be fragmented" flag is set to 1, and

3.Remaining status report request flags must be zero.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 4.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle processing control flags are defined in RFC 5050 section 4.2. A&quot;dtn:none&quot; source endpoint ID means the bundle is not uniquelyidentifiable. The features that rely on bundle identity are the bundle&#x27;scustody transfer requested flag must be zero, the &quot;Bundle must not befragmented&quot; flag must be 1, and all status report request flags must bezero.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>The requirement is considered verified when a code inspection shows abundle&#x27;s identity is disabled when the endpoint ID=“din:none”, the custodytransfer flag = 0; the “Bundle must not be fragmented” flag = 1, andremaining status report flags = 0.</td></tr></table>

## BPv6-021 Primary Bundle Block

Bundles created by a source bundle protocol agent shall have a unique combination of source endpoint ID and bundle creation timestamp.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 4.5.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Creation timestamp is defined in RFC 5050 section 4.5.1. Thecombination of source endpoint ID and bundle creation timestamptherefore serves to identify a single transmission request, enabling it to beacknowledged by the receiving application (provided the source endpointID is not &quot;dtn:none&quot;).</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives multiple bundles from HDTN and confirms all bundles have aunique combination of source endpoint ID and bundle creation timestamp.</td></tr></table>

## BPv6-022 Constraining Bundle Fragmentation 1

The concatenation of fragments shall result in a payload identical to the bundle that was fragmented.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle fragmentation is defined in RFC 5050 section 5.8. The payloads offragments resulting from different fragmentation episodes, in differentparts of the network, may be overlapping subsets of the original bundle&#x27;spayload.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a received reassembledbundle&#x27;s payload is identical to the original payload prior to fragmentation.</td></tr></table>

## BPv6-023 Constraining Bundle Fragmentation 2

The primary block's bundle processing flags of each fragment shall indicate that the bundle is a fragment.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle structure is defined in RFC 5050 section 5.8. Keeping track offragmented bundles is imperative for network management.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a fragmented bundle from BPGen, BPSendFile, and HDTN andconfirms the bundle has the primary block bundle processing flags set totrue.</td></tr></table>

## BPv6-024 Constraining Bundle Fragmentation 3

The end of each fragment's primary bundle block shall contain the fragment offset followed by the total application data unit length.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle structure is defined in RFC 5050 section 5.8. Keeping track offragmented bundles is imperative for network management. The fragmentoffset and total application data unit length aids in reconstructing thebundle once it reaches its destination.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a fragmented bundle from BPGen, BPSendFile, and HDTN andconfirms the end of each received fragment contains the fragment offsetfollowed by the total application data unit length.</td></tr></table>

## BPv6-025 Bundle Fragmentation Replication

When the 'Block must be replicated in every fragment' bit is 1, then the block shall be replicated in the fragment(s).

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle structure is defined in RFC 5050 section 5.8. The &quot;Block must bereplicated in every fragment&quot; bit, when true, means that the block shall bereplicated in every fragment.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a fragmented bundle from BPGen, BPSendFile, and HDTN andconfirms the bundle contains a block with the specified bit set to 1 and thespecified block is shown to be replicated in each fragment.</td></tr></table>

## BPv6-026 Bundle Fragmentation Order

The relative order of the blocks that are present in a fragment shall be the same as in the bundle prior to fragmentation.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle structure is defined in RFC 5050 section 5.8. Keeping block orderduring fragmentation is imperative for network management; will aid inreconstructing the bundle once it reaches its destination.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when fragmenting a bundleshows the blocks are kept in the same order as the bundle prior tofragmentation.</td></tr></table>

## BPv6-027 SDNV MSB

An SDNV encoded in N octets shall have the MSB of every octet set to 1, excluding the last octet.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>SDNVs are defined in RFC 5050 section 4.1. An SDNV is a numericvalue. The value encoded in an SDNV is the unsigned binary numberobtained by concatenating into a single bit string the 7 least significant bitsof each octet of the SDNV. The last of an SDNV string has its mostsignificant bit (MSB) set to zero.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a received bundle isencoded in N octets with the MSB of every octet set to 1 excluding the lastoctet.</td></tr></table>

## BPv6-028 Dictionary Revision

When removal of a string from the dictionary changes the offsets of other strings in the dictionary, endpoint ID references that refer to the other strings shall be adjusted.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 4.7</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Dictionary revision(s) are defined in RFC 5050 section 4.7. Note thatthese references may be in the primary block and/or in the block EIDreference fields of extension blocks.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when the removal of a string fromthe dictionary that causes the offsets of other strings to change results inendpoint ID references that refer to those strings being adjusted.</td></tr></table>

## BPv6-029 Bundle Reception Unintelligible

The bundle protocol agent shall delete the bundle for the reason "Block unintelligible" for any extension block that the bundle protocol agent cannot process.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>To keep the network efficient, anything the network doesn&#x27;t recognize willbe discarded.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatsends a bundle with a corrupt extension block to HDTN and is confirmedthat block has been deleted.</td></tr></table>

## BPv6-030 Removal of a Block from a Bundle

When the block is indicated to be discarded then the bundle protocol agent shall remove this block from the bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>To keep the network efficient, anything the network doesn&#x27;t recognize willdiscard. This indication is shown by the block processing flags. Thecriteria to remove the block from the bundle is if the flags in that block doNOT indicate that the bundle must be deleted in this event but do indicatethat the block must be discarded.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatsends a bundle containing an &quot;un-processable&quot; block with the specifiedflag set to HDTN and the block is shown to have been deleted.</td></tr></table>

## BPv6-031 Bundle Reception Block Process Flag

The bundle protocol agent shall set the "Block was forwarded without being processed" flag to 1 in the block processing flags of the block when the block cannot be processed.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The &quot;block was forwarded without being processed&quot; flag will not be 1 if theblock processing flags in that block indicate that the bundle must bedeleted or that the block must be discarded</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a bundle with an un-processable block is sent to HDTN and the block is shown to have beenupdated with the &quot;Block was forwarded without being processed&quot; flag setto 1.</td></tr></table>

## BPv6-032 Bundle Reception Custody Failure

For a singleton endpoint bundle with custody transfer redundancy, the bundle protocol agent shall generate a "Failed" custody signal via a flag.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Procedures for handling redundancy in custody transfer for a bundlewhose destination is not a singleton endpoint are not defined in the RFC5050 specification. The specific flag to be set for this bundle is &quot;redundantreception&quot; reason code. This happens when receiving a redundant singleendpoint bundle.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatsends a singleton endpoint bundle with custody transfer redundancy toHDTN and confirms a &quot;Failed&quot; custody signal is generated with the&quot;redundant reception&quot; flag set.</td></tr></table>

## BPv6-033 Reporting of Custodial Delivery

When the bundle's custody transfer requested flag (in the bundle processing flags field) is set to 1, custodial delivery shall be reported.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.7</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Procedures for reporting custodial delivery for a bundle whose destinationis not a singleton endpoint are not defined in the RFC 5050 specification.Network management is necessary for determining the health andstatistics of the network.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatsends a bundle to HDTN with the &quot;custody transfer requested&quot; flag setand confirms that custodial delivery is reported.</td></tr></table>

## BPv6-034 Local Bundle Delivery Succeeded Response

When a bundle contains a singleton endpoint destination, the bundle protocol agent shall report custodial delivery by generating a "Succeeded" custody signal for the bundle, destined for the bundle's current custodian.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.7</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>When custody is enabled a handshake happens between the two nodes.Details of bundle acceptance is defined in RFC 5050 section 5.7.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatsends a single destination bundle with custody transfer enabled to HDTNand confirms a &quot;succeeded&quot; custody signal is generated.</td></tr></table>

## BPv6-035 Block Processing Control Flags Zeroing Flags

The 'Block must be replicated in every fragment' bit in the block processing flags field shall be set to zero on the blocks that follow the payload block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 4.3</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>When a bundle is fragmented, it fragments itself at the payload blocktherefore fragmenting all blocks after the payload block too. Bundletransmission service is defined in RFC 5050 section 4.3.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a fragmented bundle from BPGen, BPSendFile, and HDTN andconfirms all fragments have the specified bit set to zero for blocksfollowing the payload block.</td></tr></table>

## BPv6-036 Bundle Transmission Commit to Custody

When custody transfer is requested, the bundle protocol agent shall commit to accepting custody of the bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>When custody is enabled, custody rules remain through the lifetime of thebundle. In terms of bundle transmission services regarding custodytransfer are defined in RFC 5050 section 5.2.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatsends a bundle with custody to HDTN and confirms that HDTN commits toaccepting custody of the bundle.</td></tr></table>

## BPv6-037 Bundle Transmission Source Endpoint

The source endpoint ID of the bundle shall be either the ID of an endpoint of which the node is a member or the null endpoint ID "dtn:none".

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The bundle transmission service details are defined in RFC 5050 section5.2. The source endpoint ID is the same ID as the node that created it.This allows network users to pinpoint which node created the bundle.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives of bundle with custody from BPGen, BPSendFile, and HDTN andconfirms the bundle has a source endpoint ID of the sending node.</td></tr></table>

## BPv6-038 Bundle Forwarding Contraindication Lookup

When the bundle's Status Report Reason Codes are zero, the bundle protocol agent shall allow a bundle to be forwarded.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Contraindication reasons are defined in Figure 12 of RFC 5050.Contraindication is placed upon a bundle whenever the bundle protocolagent needs to do something else with the bundle for any reason.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatsends a bundle with status report reason codes set to zero to HDTN andconfirms the bundle is forwarded.</td></tr></table>

## BPv6-039 Bundle Forwarding Choosing Endpoint

The bundle protocol agent shall determine the endpoint(s) to forward the bundle to.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The bundle protocol agent may choose either to forward the bundledirectly to its destination endpoint (if possible) or to forward the bundle tosome other endpoint(s) for further forwarding. The manner in which thisdecision is made may depend on the scheme name in the destinationendpoint ID but is beyond the scope of this document. If the agent finds itimpossible to select any endpoint(s) to forward the bundle to, thenforwarding is contraindicated.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatsends a bundle to HDTN and confirms HDTN sets the next hop of thebundle.</td></tr></table>

## BPv6-040 Bundle Forwarding Block Sequencing

The sequencing of the blocks in a forwarded bundle shall remain the same as the bundle transits a node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle forwarding block sequencing is defined in RFC 5050 section 5.4.Keeping the block sequencing between hops will avoid the possibility ofinvalidating bundle security.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatsends a bundle to HDTN and confirms HDTN does not alter the order ofthe bundle blocks.</td></tr></table>

## BPv6-041 Bundle Forwarding Reason Code

When the bundle requires a reason code without any constraints, then the reason code shall be "no additional information".

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle forwarding is defined in RFC 5050 section 5.4. Bundles mayrequire reason codes even if it is not contraindicated.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle status report from BPGen, BPSendFile, and HDTN andconfirms the reason code is set to &quot;no additional information&quot; by default.</td></tr></table>

## BPv6-042 Forwarding Contraindicated Decision

The bundle protocol agent shall determine when forwarding is contraindicated based on RFC 5050 Figure 12: Status Report Reason Codes.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle forwarding is defined in RFC 5050 section 5.4.1. If the bundleprotocol agent decides that the bundle failed to forward, it is likely to beinfluenced by the reason for which forwarding is contraindicated.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when the failure signal isreceived and then the bundle is resent.</td></tr></table>

## BPv6-043 Forwarding Failed Custody Signal Current Custodian

When a bundle has a singleton endpoint destination, the bundle protocol agent shall handle the custody transfer failure by generating a "Failed" custody signal for the bundle that is destined for the bundle's current custodian.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.4.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>When custody is enabled, custody rules remain through the lifetime of thebundle. Custody deletion is defined in RFC 5050 section 5.4.2.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatsends a bundle with custody to an HDTN node that is unable to acceptcustody and confirms that a &quot;failed&quot; custody signal is generated.</td></tr></table>

## BPv6-044 Forwarding Failed Reason Code

When forwarding fails, the custody signal shall contain a reason code indicating the reason for the failure.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.4.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle forwarding rules are defined in RFC 5050 section 5.4.2. Thecustody signal contains, when applicable, the contraindication when abundle uses reliability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatsends a bundle with custody to an HDTN node that is unable to forward itand confirms a failed custody signal is generated containing the reasoncode for the failure.</td></tr></table>

## BPv6-045 Bundle Expiration

When a bundle expires, the bundle protocol agent shall delete the bundle for the reason "lifetime expired".

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.5</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle forwarding rules for expired bundles are defined in RFC 5050section 5.5. Network needs not to waste resources moving expired data.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatsends an expired bundle to HDTN and confirms the expired bundle isdeleted from HDTN storage.</td></tr></table>

## BPv6-046 Bundle Discard Prevented

When deletion of the singleton endpoint bundle is prevented from being discarded, then a bundle deletion status report citing the reason for deletion shall be generated.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.13</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle deletion is defined in RFC 5050 section 5.13. There are extraprocedures for bundles which utilize reliability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a code inspection shows abundle deletion status report when a bundle is prevented from beingdiscarded.</td></tr></table>

## BPv6-047 Bundle Deletion

To delete a bundle, a bundle’s retention constraints shall be removed.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.13</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle deletion procedures are defined in RFC 5050 section 5.13.Network management needs to account for data delivered.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a code inspection shows theremoval of a bundle&#x27;s retention constraints</td></tr></table>

## BPv6-048 Generation of Bundle Deletion Status Report

A bundle deletion status report shall be generated after the deletion of a bundle for which custody transfer is requested.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Administrative record definitions are defined in RFC 5050. Reports aid innetwork statistics.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a code inspection shows ageneration of a bundle deletion status report when custody transfer wasrequested.</td></tr></table>

## BPv6-049 Intermittent Connectivity Conditions

The DTN implementation shall store data when there is intermittent connectivity.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>DTN is store, carry, forward. This is due to the intermittent nature thatDTN is used.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatsends a bundle to an HDTN node with no other connectively and confirmsthat the bundle is stored.</td></tr></table>

## BPv6-050 Late Binding

The DTN implementation shall provide dynamic EID binding capabilities.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Late binding capabilities are mentioned in RFC 5050 section 1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a code inspection shows adynamic EID binding capability.</td></tr></table>

## BPv6-051 Custody Acceptance Succeeded Signal

The bundle protocol agent shall generate a "Succeeded" custody signal for the bundle, destined for the bundle's current custodian, when accepting custody.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6, RFC 5050 Section 5.10.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>When custody is enabled, a handshake happens between the two nodes.Details of custody signal processing is defined in RFC 5050 section5.10.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatsends a bundle with custody to HDTN and confirms a &quot;succeeded&quot;custody signal is generated.</td></tr></table>

## BPv6-052 Retransmit After Custody Transfer Timer Expiration

When custody transfer has failed by the custody transfer timer expiration, the DTN implementation shall retransmit the bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>When custody is enabled, a handshake happens between the two nodes.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a bundle with custody isretransmitted when the bundle had an expired custody transfer timerexpiration.</td></tr></table>

## BPv6-053 Retransmit After Custody Signal Reception Failure

When a failed custody signal has been received, the bundle agent shall retransmit the bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>When custody is enabled, a handshake happens between the two nodes.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a bundle with custody isretransmitted.</td></tr></table>

## BPv6-054 Bundles Retained for Forwarding

Bundle state information of BP nodes shall provide the number of bundles in storage at the current node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F1 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided from thecurrent node providing the number of bundles in storage.</td></tr></table>

## BPv6-055 Bundles Retained for Transmission

Bundle state information of BP nodes shall provide the number of bundles queued for transmission at the current node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F1 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided from thecurrent node providing the number of bundles queued for transmission.</td></tr></table>

## BPv6-056 Bundles Retained for Custody Acceptance

Bundle state information of BP nodes shall provide the number of bundles retained for custody acceptance at the current node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F1 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided from thecurrent node providing the number of bundles retained for custodyacceptance.</td></tr></table>

## BPv6-057 Bundles Retained for Reassembly

Bundle state information of BP nodes shall provide the number of bundles retained for reassembly at the current node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F1 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided from thecurrent node providing the number of bundles retained for reassembly.</td></tr></table>

## BPv6-058 Bulk Bundles Sourced

Bundle state information of BP nodes shall provide the number of bundles generated by the current node with the bulk priority.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F1 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided from thecurrent node providing the number of bundles generated with bulk priority.</td></tr></table>

## BPv6-059 Normal Bundles Sourced

Bundle state information of BP nodes shall provide the number of bundles generated by the current node with the normal priority.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F1 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided from thecurrent node providing the number of bundles generated with normalpriority.</td></tr></table>

## BPv6-060 Expedited Bundles Sourced

Bundle state information of BP nodes shall provide the number of bundles generated by the current node with the expedited priority.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F1 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided from thecurrent node providing the number of bundles generated with expeditedpriority.</td></tr></table>

## BPv6-061 Bulk Bundles Queued

Bundle state information of BP nodes shall provide the number of bundles with the bulk priority currently resident on the node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F1 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided from thecurrent node providing the number of bundles with bulk priority.</td></tr></table>

## BPv6-062 Normal Bundles Queued

Bundle state information of BP nodes shall provide the number of bundles with the normal priority currently resident on the node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F1 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided from thecurrent node providing the number of bundles with normal priority.</td></tr></table>

## BPv6-063 Expedited Bundles Queued

Bundle state information of BP nodes shall provide the number of bundles with the expedited priority currently resident on the node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F1 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided from thecurrent node providing the number of bundles with expedited priority.</td></tr></table>

## BPv6-064 Fragmentation

Bundle state information of BP nodes shall provide the number of bundles that have been fragmented by this node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F1 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided with thenumber of bundles that have been fragmented by the tested node.</td></tr></table>

## BPv6-065 Number of Fragments

Bundle state information of BP nodes shall provide the number of fragments created by this bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F1 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided with thenumber of fragments which were created by the tested node.</td></tr></table>

## BPv6-066 Failed Custody Transfers

Error and reporting information of BP nodes shall provide the number of custody failed incoming bundles at this node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F2 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided with thenumber of incoming bundles that had a request for custody failed at thetested node.</td></tr></table>

## BPv6-067 Failed Forwards

Error and reporting information of BP nodes shall provide the number of bundles that have experienced a forwarding failure at this node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F2 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided with thenumber of incoming bundles that had experienced a forwarding failure atthe node.</td></tr></table>

## BPv6-068 Abandoned Delivery

Error and reporting information of BP nodes shall provide the number of abandoned bundles at this node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F2 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided with thenumber of incoming bundles that had delivery abandoned at the node.</td></tr></table>

## BPv6-069 Discarded Bundles

Error and reporting information of BP nodes shall provide the number of bundles discarded at this node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F2 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided with thenumber of bundles that have been discarded at the node.</td></tr></table>

## BPv6-070 Activity State

Registration information of BP nodes shall provide the Endpoint ID of this registered endpoint.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F3 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is providedcontaining the endpoint ID of the registered endpoint.</td></tr></table>

## BPv6-071 Singleton State

Registration information of BP nodes shall provide the current state of the EID, at the time the managed information was queried.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F3 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided with thequeried current state of the EID.</td></tr></table>

## BPv6-072 Default Failure Action

Registration information of BP nodes shall provide whether this EID is a singleton EID.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F3 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided with thenode&#x27;s EID classification.</td></tr></table>

## BPv6-073 Node Identifier

Registration information of BP nodes shall provide the default action to be taken when delivery is not possible.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F3 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided with thedefault action the node takes when delivery is not possible.</td></tr></table>

## BPv6-074 Bundle Protocol Version Number

Node state information of BP nodes shall provide the Endpoint ID that uniquely and permanently identifies this node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F4 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided with thenode&#x27;s Endpoint ID that is unique and permanent to the node.</td></tr></table>

## BPv6-075 Available Storage

Node state information of BP nodes shall provide the number of the version of the Bundle Protocol that is supported at this node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F4 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided with thesupported BP version for the node under test.</td></tr></table>

## BPv6-076 Last Up Time 1

Node state information of BP nodes shall provide the number of kilobytes of storage allocated to bundle retention at this node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F4 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report provides thenumber of kilobytes of storage allocated to bundle retention and thenumber of kilobytes of storage available to store bundles at the nodeunder test.</td></tr></table>

## BPv6-077 Last Up Time 2

Node state information of BP nodes shall provide the number of kilobytes of storage available to store bundles at this node and the number of kilobytes of storage available to store bundles.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F4 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report provides thenumber of kilobytes of storage allocated to bundle retention and thenumber of kilobytes of storage available to store bundles at the nodeunder test.</td></tr></table>

## BPv6-078 Extension Name

Node state information of BP nodes shall provide the name identifying one of the BP extensions supported per extension at this node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and MIB</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is stated in the CCSDS blue book table F4 forstandardized metrics. Utilizing standardized metrics aids in networkmanagement and interoperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a report is provided with thenode&#x27;s BP supported extensions.</td></tr></table>

## BPv6-079 State of the Node Managed Information

BP node(s) shall support a set of managed information that represents the state of the node at a particular time.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>CCSDS 734.2-B-1 Table A6 and A6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Adding time into the managed information aids in statistical analysisand/or network health monitoring.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when a code inspection shows aset of managed information that is to be gathered.</td></tr></table>

## 2 BPV7 REQUIREMENTS

## BPv7-001 CBOR Encoding

The data type for bundle block fields shall be CBOR unsigned integers.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>CBOR is the encoding for bundle fields. BP v7 only uses unsignedintegers, byte strings, and array.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an inspection of thecode shows that data type for bundle block fields are CBOR unsignedintegers.</td></tr></table>

## BPv7-002 Bundle Structure

Bundles shall be a CBOR indefinite-length array.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>CBOR is the encoding for bundle fields. BP v7 only uses unsignedintegers, byte strings, and array. Bundle structure is defined in RFC 9171section 4.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an inspection of thecode shows that bundles are a CBOR indefinite-length array.</td></tr></table>

## BPv7-003 Bundle Array Structure

Bundle arrays shall have a length of at least two blocks.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Primary bundle block and payload bundle block is the minimumrequirement for a bundle. Bundle structure is defined in RFC 9171section 4.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle from HDTN and confirms that the bundle array has alength of at least two blocks.</td></tr></table>

## BPv7-004 Block Order

Block(s) following the primary block shall be a canonical block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Canonical blocks are the extension blocks for when data is added to thebundle header total for extra information. Block order is defined in RFC9171 section 4.1 and 4.3.2.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle from HDTN and confirms the block following theprimary block conforms to the canonical block format.</td></tr></table>

## BPv7-005 Bundle Structure Stop Code

A CBOR "break" stop code, terminating the array, shall be directly after the payload block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The stop code tells the node that the bundle is finished. Block order isdefined in RFC 9171 section 4.1</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle from HDTN and confirms the payload block isterminated by the CBOR &quot;break&quot; stop code.</td></tr></table>

## BPv7-006 Bundle Encoding

The CBOR encodings values of block fields shall conform to the core deterministic encoding requirements specified in the data dictionary, except indefinite-length items.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Indefinite length items are not prohibited within the BPv7 specification.CBOR, from RFC 8949, is specified as the encoding scheme per RFC9171.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an inspection of thecode shows all values in block fields are CBOR encodings.</td></tr></table>

## BPv7-007 Primary Bundle Location

The first block in the bundle shall be a primary bundle block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The location of the primary bundle block is defined in RFC 9171section 4.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle from HDTN a confirms the first block is a primarybundle block.</td></tr></table>

## BPv7-008 Number of Primary Blocks

A bundle shall have exactly one primary bundle block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Number of primary bundle blocks is defined in RFC 9171 section 4.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle from HDTN and confirms there is only one primarybundle block.</td></tr></table>

## BPv7-009 Payload Block Location

The last bundle block shall be a payload block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The location of the payload block is defined in RFC 9171 section 4.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle from HDTN and confirms the last block in the bundle isa payload block.</td></tr></table>

## BPv7-010 Number of Payload Blocks

A bundle shall have exactly one payload block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The payload contains the message which can be either data, information,or communication. Number of payload bundle blocks is defined in RFC9171 section 4.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle from HDTN and confirms the bundle has exactly oneprimary bundle block.</td></tr></table>

## BPv7-011 CRC Types

CRC type will specify omitted, X-25 CRC-16, or CRC32C CRC-32.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.2.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>CRC type is defined in RFC 9171 section 4.2 and 4.3.1. CRC valuesexplain if CRC is calculated or not.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an inspection of thecode shows the CRC type as omitted, X-25 CRC-16, or CRC32C CRC-32.</td></tr></table>

## BPv7-012 Bundle Processing Control Flags

The bundle processing control flags shall be processed as a bit field.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.2.3</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bit field values are defined in the data dictionary. Control flag values aredefined in RFC 9171 section 4.2.3 with details on page 14.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an inspection of thecode shows a bit field for the bundle processing control flags.</td></tr></table>

## BPv7-013 Control Flags for ADU

When bundle processing control flag "ADU is an administrative record" bit is TRUE, then all status report request flag values shall be FALSE.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.2.3</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Control flag values are defined in RFC 9171 Section 4.2.3.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle with the &quot;ADU is administrative record&quot; bit set to TRUEand confirms that all status report request flags values are set to 0.</td></tr></table>

## BPv7-014 Omitting Source Node Flag

When all of the following bundle processing control flag bits are set to FALSE, bundle source node ID of the bundle shall be omitted:

1. "Request reporting of bundle reception"

2. "Request reporting of bundle forwarding"

3. "Request reporting of bundle delivery"

4. "Request reporting of bundle deletion"

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.2.3</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Control flag values are defined in RFC 9171 section 4.2.3</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle from HDTN with all bundle processing control flag bitsset to false and confirms the bundle source node ID has been omitted.</td></tr></table>

## BPv7-015 Block Processing Control Flags

The block processing control flags shall be processed as a bit field.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.2.4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bit fields are defined in the data dictionary. Bundle processing controlflags assert properties of the bundle as a whole. They are conveyed in theprimary block of the bundle. Control flag values are defined in RFC 9171section 4.2.4 with details on page 15 and are required to be at leastprocessed as bit field(s).</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an inspection of thecode shows the block processing control flag values as bit fields.</td></tr></table>

## BPv7-016 The dtn URI Scheme-SSP

When the string value of a BP endpoint ID's Scheme-Specific Part (SSP) is equal to "none", the SSP shall be set to an unsigned integer value of zero.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.2.5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The scheme identified by the &lt; scheme name &gt; in an endpoint ID is a setof syntactic and semantic rules that fully explain how to parse andinterpret the SSP. URI scheme code definition document requirementsare defined in RFC 9171 section 4.2.5.1.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle from HDTN with the endpoint ID of &quot;dtn:none&quot; andconfirms the SSP has been set to zero.</td></tr></table>

## BPv7-017 Node ID

The EID of a node's administrative endpoint shall uniquely identify that node; no two node endpoints are the same.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.2.5.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Network management is necessary for determining the health andstatistics of the network. The administrative endpoint of a node codedefinition document requirements are defined in RFC 9171 section4.2.5.2.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an inspection of thecode shows that the EID of a node&#x27;s administrative endpoint is generatedto be unique to that node.</td></tr></table>

## BPv7-018 Keep CBOR Encoding

The CBOR- encoded values of all fields in the primary block shall remain unchanged from point-topoint.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.3.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Unchanging the primary block provides integrity and accountability of thenetwork. Rule to keep the primary block unchanged is defined in RFC9171 section 4.3.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatconfirms HDTN does not modify the CBOR-encoded values of any field inthe primary block of a bundle.</td></tr></table>

## BPv7-019 Primary Header Field Order

The fields of the primary bundle block shall be in the following order when present: version, bundle processing control flags, CRC type, destination node EID, source node EID, report-to EID, creation timestamp, lifetime, fragment offset, total Application Data Unit Length, CRC.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.3.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Primary bundle block fields explain what information is in what CBORarray. Field order of the primary bundle block is defined in RFC 9171section 4.3.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle from HDTN and confirms the primary block contents arein the specified order.</td></tr></table>

## BPv7-020 Bundle Age

When Bundle Age Block extension block is present, Bundle Age shall be obtained from the Bundle Age Block extension block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.3.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle Age Block is specifically for the bundle&#x27;s age and its computationto its expiration. Bundle Age Block details are defined in CCSDS 734.2-P-1.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle from HDTN with a Bundle Age Block present andconfirms the Bundle Age has been calculated from it.</td></tr></table>

## BPv7-021 Fragment Offset

Fragment offset shall be present in the primary block when the bundle processing control flags of the primary block indicate that the bundle is a fragment.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.3.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundles can contain the full bundle or be a subset of the bundle, i.e., afragment. Fragment Offset is defined in RFC 9171 section 4.3.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a fragmented bundle from HDTN and confirms the fragmentoffset is present.</td></tr></table>

## BPv7-022 Canonical Block Field Order

The fields of every canonical block shall be listed in order and are: Block Type Code, Block Number, Block Processing Control Flags, CRC Type, Block Type Specific Data.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.3.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Canonical bundle block(s) fields explain what information is in what CBORarray. Canonical Bundle Block is defined in RFC 9171 section 4.3.2. Note:When CRC is not present, they are omitted in the element count.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle with a canonical block from HDTN and confirms thecanonical block fields are in the specified order</td></tr></table>

## BPv7-023 CRC Computation

CRC's computation shall be performed using a concatenation of all bytes of the block with the CRC's field temporarily set to zero as the binary dividend.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.3.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>CRC aids in integrity of the bundle since it is calculated by every piece inthe header. The concatenation of all bytes of the block includes the CBOR&quot;break&quot; characters and the CRC field itself. CRC computation is defined inRFC 9171 section 4.3.1</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that thecomputed CRC value is correct when the bytes of a CRC field is zero.</td></tr></table>

## BPv7-024 Previous Node Block Format

Previous Node Block Node ID shall conform to Section 4.2.5.2 of RFC 9171.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The Previous Node Block, block type 6, identifies the node that forwardedthis bundle to the local node; its block-type-specific data is the node ID ofthe transmitter node. RFC 9171 defined Previous Node Block Node IDdetails in Section 4.4.1 and specifically calls out section 4.2.5.2.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatreceives a bundle from HDTN and confirms the previous node blockconforms to RFC 9171.</td></tr></table>

## BPv7-025 Previous Node Block Limitation

The bundle shall contain a Previous Node Block after its first hop when Previous Node Block is enabled.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>There will not be a Previous Node Block when the bundle is firstinitialized. Previous Node Block details are defined in RFC 9171section 4.4.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when enabling a PreviousNode Block and verify the creation node bundle does not contain aPrevious Node Block.</td></tr></table>

## BPv7-026 Bundle Age Instances

When the bundle's creation time is zero, then the bundle shall contain an occurrence of a Bundle Age Block extension block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 4.4.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle Age Block details are required in CCSDS 734.2-P-1.1; the bundleage units are defined in RFC 9171 section 4.4.2.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when the bundle&#x27;s creationtime is zero and contains a bundle age block.</td></tr></table>

## BPv7-027 Forwarding Bundle Failure

The BPA shall declare failure in forwarding the bundle when any reason from the IANA "Bundle Status Report Reason Codes" registry is indicated.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 5.4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>If the bundle did not send correctly, the system needs to know about it soit can correct it; a forwarding bundle failure is defined in RFC 9171 section5.4.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an inspection of thecode shows a check to the lANA &quot;Bundle Status Report Reason Codes&quot;prior to forwarding the bundle.</td></tr></table>

## BPv7-028 Forwarding Failed Procedure

Forwarding failed procedure shall be performed with Step 4 and Step 5 of Section 5.4 of RFC 9171 when Previous Node Block is enabled AND the bundle requires forwarding the bundle back to the previous node.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 5.4.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>When bundle tracking is on, then the bundle can use the trackinginformation to return back to the previous node. Details on this procedureare defined in RFC 9171 section 5.4.2.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatsends a bundle to HDTN that is unable to be forwarded and confirms thebundle is forwarded back to the sender.</td></tr></table>

## BPv7-029 Bundle Expiration Calculation

The Bundle Age Extension block shall be used for the bundle expiration calculation when the bundle expiration is not using the timestamp.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 5.5</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>If the bundle does not have the Bundle Age extension block, it may becalculated from the timestamp; not calculating the bundle expiration fromthe timestamp can be due to it being zero or the clock is untrustworthy;Bundle age is determined by subtracting the bundle&#x27;s creation timestamptime from the current time; Bundle expiration is detailed in section 5.5RFC 9171. DTN.6.10004</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when the Bundle AgeExtension block calculates the bundle expiration calculation.</td></tr></table>

## BPv7-030 Bundle Expiration Deletion

When a bundle is declared expired, the BPA shall set Status Report Reason Code to “Lifetime expired.”

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 5.5</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>There is no need for the network to hold onto an expired bundle. Bundleexpiration is detailed in section 5.5 RFC 9171.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test is performed thatsends an expired bundle to HDTN and confirms the bundle has beendeleted.</td></tr></table>

## BPv7-031 Bundle Fragmentation Payload

When fragmenting a bundle, the payload shall be split between the fragments without overlapping.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 5.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Fragments of payloads cannot overlap to avoid data being duplicated,data corruption, and non-efficient space management for the network;Bundle fragmentation is defined in section 5.8 of RFC 9171.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows a fragmented bundle is split without overlapping.</td></tr></table>

## BPv7-032 Bundle Fragmentation Concatenation

The concatenation of the payloads of all fragments produced by fragmentation shall be identical to the payload of the unfragmented bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 5.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>All payload fragments together must equal, in size and content, of theoriginal payload; Bundle fragmentation is defined in section 5.8 ofRFC 9171.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when reassembling afragmented bundle&#x27;s payload equals the original payload.</td></tr></table>

## BPv7-033 Bundle Fragmentation Primary Block Flags

Bundle processing control flags within the primary block of a fragment shall indicate that the bundle is a fragment and provides the fragment offset and the total application data unit length.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 5.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Primary block stays the same for the fragments aside from the controlflags pertaining to the specific fragment; Bundle fragmentation is definedin section 5.8 of RFC 9171.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a fragmented bundle&#x27;sbundle processing control flags show the fragment offset and the totalapplication data unit length.</td></tr></table>

## BPv7-034 Bundle Fragmentation CRC

When fragmenting a bundle, the CRC of the primary block shall be recomputed for each fragment.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 5.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundles with CRCs will need to be recalculated if it is split into fragmentedbundles. This is to ensure proper CRC values so the bundle fragment(s)aren&#x27;t subject to being a &quot;malformed bundle&quot;; Bundle fragmentation isdefined in section 5.8 of RFC 9171.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an inspection of thecode shows a recompilation of the CRC for each fragmented bundle.</td></tr></table>

## BPv7-035 Bundle Fragmentation Zero Offset Fragment

When a fragmented bundle is the zero-offset fragment, all extension blocks of the fragmented bundle shall be replicated in the fragment.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 5.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundle fragmentation is defined in section 5.8 of RFC 9171.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a fragmented bundle isflagged to be a fragmented bundle and the offset is zero for the extensionblocks of the fragmented bundle.</td></tr></table>

## BPv7-036 Bundle Fragmentation Extension Blocks

Extension blocks of a fragmented bundle with a "Block must be replicated in every fragment" flag Bundle Processing Control Flag set to TRUE shall be replicated in every fragment.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 5.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Fragments just like bundles are subject to following the flags set; Bundlefragmentation is defined in section 5.8 of RFC 9171.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when the &quot;Block shall bereplicated in every fragment&quot; flag is set to 1 in each fragment of a bundle.</td></tr></table>

## BPv7-037 Reassembly for Payloads

The reassembled ADU shall replace the payload of the zero-offset fragment.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 5.9</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Reassembly is defined in section 5.9 of RFC 9171.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when reassembling afragmented bundle&#x27;s payload equals the original payload.</td></tr></table>

## BPv7-038 Reassembly Label

The "Reassembly pending" retention constraint shall be removed from fragments with the same source node ID and creation timestamp as the original fragment.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 5.9</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to update the retention constraint to let the node know what is nextto be done; Reassembly is defined in section 5.9 of RFC 9171.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an inspection of thecode shows the &quot;Reassembly pending&quot; retention constraint is removedfrom every fragment with the same source node ID and creationtimestamp.</td></tr></table>

## BPv7-039 Retention Constraints for Deletion

When a bundle is declared for deletion, there shall be no bundle retention constraints.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 5.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>When discarding a bundle, there is no need for retention constraints sincethere will be no retention; Retention constraints for bundle deletions aredefined section 5.10 in RFC 9171.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an inspection showsthat when a bundle is declared for deletion there are not bundle retentionconstraints.</td></tr></table>

## BPv7-040 Convergence-Layer Services

Convergence-layer protocols shall provide rate limiting, congestion control or both.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 7.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Some convergence-layer protocols do not have the capabilities to handlelarge throughputs; convergence-layer protocols are defined in section 7.2of RFC 9171. HDTN only provides rate limiting convergence-layerprotocols.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an inspection showsthat the code is performing rate limiting.</td></tr></table>

## BPv7-041 Security

When requested, security shall use BPSec.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9171 Section 8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The data in the network must keep its integrity, encryption, andauthentication when required; security considerations are defined insection 8 of RFC 9171.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows thatBPSec is used when requested.</td></tr></table>

## 3 BPSEC REQUIREMENTS

## BPSec-001 Security Operation Uniqueness

BPSec shall apply one security service to a security target per bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This uniqueness requirement ensures that there is no ambiguity related tothe order in which security blocks are processed or how security policycan be specified to require certain security services be present in abundle.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when the user configuration of twosame security operations for the same target block is not allowed andgenerates an error.</td></tr></table>

## BPSec-002 Security Contexts

BPSec shall support the default security contexts in the approved security contexts registry: BCB-AES-GCM and BIB-HMAC-SHA2.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 2.4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>HDTN currently implements all default security contexts as per RFC 9173.These are the minimum security contexts that need to be supported forinteroperability.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement is considered verified when the default integrity andconfidentiality security contexts BCB-AES-GC and BIB-HMAC-SHA2 areboth part of the options security context parameters in the BPSec configfile and are working as expected.</td></tr></table>

## BPSec-003 Target Multiplicity

BPSec shall utilize a single security block to represent multiple security operations.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.3</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Reducing the number of security blocks in the bundle reduces the amountof redundant information in the bundle.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when code inspection showsthat BPSec security blocks (Bpv7AbstractSecurityBlock) support multipleresults per target.</td></tr></table>

## BPSec-004 Target Identification

BPSec shall set a security target value in a security block to the block number of the target block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>A security target must be uniquely and unambiguously identifiable whenprocessing a security block. Block number field in the extension blockshould be used for this purpose. Placing the set of target blocks coveredby operations in an easily accessible field allows Bundle Protocol Agents(BPAs) to quickly scan this field to assess whether new SecurityOperations (SOps) can be added to a bundle and whether the block hasoperations that must be processed.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when displaying the value ofthe block to which the security operation is applied matches the securitytarget field in the corresponding security extension block.</td></tr></table>

## BPSec-005 BIB Block Type

The block-type-specific data field of a BIB shall follow the structure of the ASB.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.7</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>All security blocks share the same block-type-specific data structure asthese blocks have common aspects.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when the inspection of abundle with BIB block on Wireshark shows that its block-type-specific datastructure follows the structure of the ASB.</td></tr></table>

## BPSec-006 BIB Security Targets

A security target of a BIB shall reference blocks excluding BIB or BCB.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.7</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>An appropriate target block that a BIB should be able to reference is anyblock that may have its block-type-specific-data signed.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when the user is not allowedto add a BIB with the security target as BIB or BCB.</td></tr></table>

## BPSec-007 BIB Integrity Mechanism

The security context shall utilize either:

1. Authentication mechanism.

2. An error detection mechanism.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.7</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The integrity mechanism used by the BIB is given by the security contextassociated with the BIB and may represent either signed or unsignedintegrity. In this way, BIB can be used to represent authentication (with asigned integrity mechanism) or simply error detection (with an unsignedintegrity mechanism).</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test successfullyauthenticates a security source using unsigned BIB or signed BIB.</td></tr></table>

## BPSec-008 BCB Replication in Bundle Fragments

BPSec shall set the flag ‘Block must be replicated in every fragment’ to true for a BCB which has payload as a target.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>BCB in each fragment indicates to a receiving node that the payloadportion of each fragment represents ciphertext.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>NA</td></tr></table>

## BPSec-009 BCB Processing

BPSec shall set the flag ‘Block must be removed from bundle if it cannot be processed’ to false for a BCB.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The removal of a BCB from a bundle has significant consequences sincethe BCB is the sole indication in the bundle that the BCB target block(s)have had their block-type-specific-data field encrypted. Removing a BCBwould make it impossible for future BPAs to decrypt the block.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when code inspection showsthat BCB has &quot;Block must be removed from bundle if it cannot beprocessed&#x27; flag set to false.</td></tr></table>

## BPSec-010 BCB Block Type

The block-type-specific data fields of a BCB shall follow the structure of the ASB.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>All security blocks share the same block-type-specific data structure asthese blocks have common aspects.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when the inspection of abundle with BCB block on Wireshark shows that its block-type-specificdata structure follows the structure of the ASB.</td></tr></table>

## BPSec-011 BCB Security Targets

A security target of a BCB shall reference either:

1. The payload block.

2. A non-security extension block.

3. A BIB.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>An appropriate target block that a BCB should be able to reference is anyblock that may have its block-type-specific-data encrypted. Only payload,non-security extension blocks and BIB blocks are allowed to be encryptedfor proper processing of bundles. A BCB MUST NOT include another BCBas a security target as other BCBs in a bundle cannot be encrypted. Doingso would hide the fact that other blocks in a bundle have been encryptedand removes the ability to decrypt them.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when the user is allowed toadd any of the following blocks as a security target of BCB the payloadblock, a non-security extension block or a BIB and is not allowed toinclude another BCB as a security target.</td></tr></table>

## BPSec-012 BCB Disallowed Security Targets 1

A BCB shall target blocks excluding the primary block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Encrypting the primary block hides bundle identity.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when the user is not allowedto add the payload block as a target for a BCB.</td></tr></table>

## BPSec-013 BCB Disallowed Security Targets 2

A BCB shall target a BIB only when sharing a security target with that BIB.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Encrypting a BIB and not the target block of the BIB removes the ability tocheck the integrity of that target block.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when the user is allowed toadd BIB as a security target for a BCB only if the BCB shares a securitytarget with that BIB.</td></tr></table>

## BPSec-014 Authenticated Encryption with Associated Data

A BCB shall utilize a confidentiality cipher that provides Authenticated Encryption with Associated Data (AEAD).

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This allows confirming that ciphertext, block processing flags and otherblocks in the bundle have not been modified.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test of confidentialityusing an authentication tag successfully verifies that ciphertext andadditional specified blocks in the bundle have not been modified.</td></tr></table>

## BPSec-015 Authentication Tag Placement

Additional information created by the cipher suite shall be placed either in:

1. The security result field.

2. The generated ciphertext.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Security contexts used by the BCB must specify whether theauthentication tag is included in the BCB as a security result or whether itis represented with the ciphertext that replaces the security target block&#x27;splaintext.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that theuser is able to configure an authentication tag to be included either in theBCB as a security result or in the ciphertext that replaces the securitytarget block&#x27;s plaintext.</td></tr></table>

## BPSec-016 Encryption in Place

When applying a BCB, BPSec shall encrypt the security target body data ‘in-place’.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This eliminates the need to move the data making the encryption fasterand more reliable and provides better performance.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an inspection of thecode of encryption function shows that encryption was performed in place.</td></tr></table>

## BPSec-017 BCB and BIB Blocks Interactions 1

When adding a BCB to a bundle with matching security targets of an existing BIB targets, then BPSec shall encrypt the existing BIB.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.9</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is needed to handle the special case of protecting the plaintextintegrity of the target block when that plaintext had been replaced byciphertext.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that whenadding a BCB to a bundle, if some (or all) of the security targets of theBCB match all of the security targets of an existing BIB, then the existingBIB is also be encrypted.</td></tr></table>

## BPSec-018 BCB and BIB Blocks Interactions 2

When adding a BCB to a bundle with matching security targets of an existing BIB security targets, then BPSec shall remove the security results associated with the BCB security targets from that BIB and place them in a new encrypted BIB.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.9</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This processing rule prevents security information about the unencryptedtarget block from persisting after the target block has been encrypted.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when adding a BCB to abundle, if some (or all) of the security targets of the BCB match some (butnot all) of the security targets of a BIB, then any security results in the BIBassociated with the BCB security targets is removed from the BIB andplaced in a new encrypted BIB.</td></tr></table>

## BPSec-019 BCB and BIB Blocks Interactions 3

BPSec shall prevent a BIB addition for a security target that is already the security target of a BCB.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.9</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is needed to not cause ambiguity in block processing order.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when the user is preventedfrom adding a BIB for a security target that is already the security target ofa BCB.</td></tr></table>

## BPSec-020 BCB and BIB Blocks Interactions 4

BPSec shall check a BIB integrity value when the BIB data is unencrypted.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.9</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>A BIB integrity value MUST NOT be checked if the BIB is the securitytarget of an existing BCB as in this case, the BIB data is encrypted.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that whenBIB is the security target of an existing BCB, that BIB is encrypted and notchecked when processing the security result.</td></tr></table>

## BPSec-021 BCB and BIB Blocks Interactions 5

BPSec shall check a BIB integrity value when the corresponding security target data is unencrypted.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.9</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>A BIB integrity value MUST NOT be checked if the security targetassociated with that value is also the security target of a BCB. In such acase, the security target data contains ciphertext as it has beenencrypted.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that whenBIB has the same security target as a BCB, that BIB is not checked.</td></tr></table>

## BPSec-022 BCB and BIB Blocks Interactions 6

BPSec shall prevent a BIB from having a BCB for its security target.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 3.9</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>An appropriate target block that a BIB should be able to reference is anyblock that may have its block-type-specific-data signed.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when the user is preventedfrom adding a BCB as a security target for a BIB.</td></tr></table>

## BPSec-023 Canonical Form of the Primary Block

Concise Binary Object Representation (CBOR) values from the primary block shall be canonicalized using the rules for Deterministically Encoded CBOR.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Canonicalization algorithms transcode the contents of a security targetinto a canonical form. Security services require consistency anddeterminism in how information is presented to cipher suites at securitysources, verifiers, and acceptors.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an inspection of thecode and bundle with BPSec enabled shows that the primary block iscanonicalized using the rules for Deterministically Encoded CBOR.</td></tr></table>

## BPSec-024 Non-Primary Block Structure

Non-primary blocks shall share the same block structure.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Security services require consistency and determinism in how informationis presented to cipher suites at security sources, verifiers, and acceptors.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when code inspection showsthat all non-primary blocks share the same block structure.</td></tr></table>

## BPSec-025 Canonical Form of the Non-Primary Block

Non-primary blocks shall be canonicalized.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>To ensure that if the values of a security target are unchanged, then thecanonical form of that target will be the same even if the encoding ofthose values for wire transmission is different.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an inspection of thebundle with BPSec enabled on Wireshark shows it has all its non-primaryblocks canonicalized.</td></tr></table>

## BPSec-026 Canonical Form Non-Primary Block CBOR Values

CBOR values from the non-primary block shall be canonicalized using the rules for Deterministically Encoded CBOR.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Security services require consistency and determinism in how informationis presented to cipher suites.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test and Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an inspection of thecode and bundle shows that CBOR values from the non-primary blockshall be canonicalized using the rules for Deterministically EncodedCBOR.</td></tr></table>

## BPSec-027 Canonical Form

Only the block-type-specific data field shall be provided to a cipher suite for encryption.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>BPSec operates on data fields within bundle blocks (e.g., the block- type-specific data field). In their canonical form, these fields shall include theirown CBOR encoding and not any other encapsulating CBOR encoding.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when code inspection of theencryption crypto function shows that only block-type-specific data field isprovided as input for encryption.</td></tr></table>

## BPSec-028 Canonical Form of the Other Blocks Encryption

Only the block-type-specific data within a non-primary block shall be encrypted and included in the canonical form used by the cipher suite for encryption.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>BPSec operates on data fields within bundle blocks (e.g., the block- type-specific data field). In their canonical form, these fields shall include theirown CBOR encoding and not any other encapsulating CBOR encoding.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a Wireshark inspectionof bundle with BCB only has the block-type-specific data within a non-primary block encrypted and included in the canonical form used by thecipher suite for encryption.</td></tr></table>

## BPSec-029 Canonical Form of the Other Blocks Decryption

Only the block-type-specific data within a non-primary block shall be decrypted and included in the canonical form used by the cipher suite for decryption.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>BPSec operates on data fields within bundle blocks (e.g., the block- type-specific data field). In their canonical form, these fields shall include theirown CBOR encoding and not any other encapsulating CBOR encoding.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a Wireshark inspectionof bundle with BCB only has the block-type-specific data within a non-primary block decrypted and included in the canonical form used by thecipher suite for decryption.</td></tr></table>

## BPSec-030 Associated Authenticated Data

BPSec shall apply an integrity-protection mechanism to non block-type-specific data fields within a nonprimary block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This allows confirming that other blocks in the bundle have not beenmodified.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test and Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that whenauthentication tag is configured, an integrity-protection mechanism isapplied to those additional fields.</td></tr></table>

## BPSec-031 Receiving BCBs 1

When a received bundle contains a BCB, the receiving node shall determine whether it is the security acceptor for any of the security operations in the BCB.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is because the acceptor does the final processing of the securityoperation and is the only node which decrypt and process the securityoperations in the BCB.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that there&#x27;s a check for whether the node is a security acceptorbefore processing any security operations in the BCB.</td></tr></table>

## BPSec-032 Receiving BCBs 2

BPSec shall process the targets according to the security policy after a failed confidentiality security operation.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>In case of security operation failure, the action for target processing isbased on the security policy configured by the user.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that if anode that is the security acceptor or verifier for any of the securityoperations in the BCBs, and the security verification fails, the target shallbe processed as specified in the BPSec config file.</td></tr></table>

## BPSec-033 Receiving BCBs 3

BPSec shall generate a bundle status report indicating the failure of a confidentiality security operation.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>In case of security operation failure, a bundle status report generation willhelp for debugging and tracking these failures.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that if anode that is the security acceptor or verifier for any of the securityoperations in the BCBs, and the security verification fails, a bundle statusreport with a failure reason code is generated.</td></tr></table>

## BPSec-034 Receiving BCBs 4

When the receiving node is the destination of the bundle, the node shall decrypt BCBs remaining in the bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The bundle destination is, by necessity, the acceptor of any blockremaining in the bundle. Since a bundle will no longer exist afterprocessing at this BPA, all blocks need to be accepted prior to passing thebundle payload to applications resident on the destination BPA.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that if anode that is the bundle final destination receives a bundle which hasmultiple BCBs, it successfully verifies, decrypts all ciphertext and removesall BCBs from the bundle.</td></tr></table>

## BPSec-035 Receiving BCBs 5

When the receiving node is not the destination of the bundle, the node shall process the BCB in accordance with the security policy.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>If the receiving node is a verifier, it shall process the BCB based on theconfigured security policy.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test has a verifiernode that is able to successfully process the BCBs according to thesecurity policy in the BPSec config file.</td></tr></table>

## BPSec-036 Receiving BCBs 6

When the security policy of a node requires a node to apply confidentiality to a specific security target and no such BCB is present in the bundle, the node shall process this security target in accordance with the security policy.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>HDTN removes the security target from the bundle because theconfidentiality (and possibly the integrity) of the security target cannot beguaranteed.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows If thesecurity policy of a node specifies that a node should have appliedconfidentiality to a specific security target and no such BCB is present inthe bundle, then the security target is removed from the bundle.</td></tr></table>

## BPSec-037 Receiving BCBs 7

When the security processing results in the removal of the payload block BPSec shall discard the bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The payload is required in a bundle.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test where BCBprocessing results in payload block removal results in discarding thebundle.</td></tr></table>

## BPSec-038 Receiving BCBs 8

The bundle shall be discarded when BPSec fails to decrypt the encrypted payload block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is a security failure meaning the bundle could be compromised.However, the payload block is required in a bundle so the whole bundle isdiscarded in this case.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that whenat the receiving security verifier or acceptor node an encrypted payloadblock cannot be decrypted, the bundle is discarded and processed nofurther (we use incorrect key to test this scenario).</td></tr></table>

## BPSec-039 Receiving BCBs 9

When an encrypted security target other than a payload block cannot be decrypted, then BPSec shall discard the target and the corresponding security blocks.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is a security failure meaning the bundle could be compromised, sothe corresponding target and security blocks should be discarded.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that whenat the receiving security verifier or acceptor node when an encryptedsecurity target other than the payload block cannot be decrypted, then theassociated security target and all security blocks associated with thattarget shall be discarded and processed no further.</td></tr></table>

## BPSec-040 Receiving BCBs 10

When the security block is deleted from a bundle, BPSec shall generate a status report showing block deletion.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Status report helps for debugging and reflecting the exact root cause ofthe failure.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that If ablock is deleted from a bundle as a result of security operation, a statusreports is generated to reflect block deletion.</td></tr></table>

## BPSec-041 Receiving BCBs 11

When a bundle is dropped following a BCB processing failure, BPSec shall generate a status report showing bundle deletion.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Status report helps for debugging and reflecting the exact root cause ofthe failure.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that If abundle is deleted as a result of security operation, a status reports isgenerated to reflect block deletion.</td></tr></table>

## BPSec-042 Receiving BCBs 12

When BPSec decrypts a BCB, the recovered plaintext for the security targets shall replace the ciphertext in the corresponding security targets’ block-type specific data fields.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The final bundle received by the application should only have decrypteddata.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a bundle inspection inWireshark at the acceptor node for a confidentiality test shows that theciphertext in the bundle was replaced with the correct plain text for thesecurity target block-type specific data field.</td></tr></table>

## BPSec-043 Receiving BCBs 13

When the plaintext is of a different size than the ciphertext, BPSec shall update the framing of the CBOR byte string of this field.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This will ensure this field remains a valid CBOR byte string.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a bundle inspection inWireshark at the acceptor node for a confidentiality test shows that if theplain text is of a different size than the ciphertext, the framing of theCBOR byte string is updated.</td></tr></table>

## BPSec-044 Receiving BCBs 14

When a BCB contains multiple security operations, each operation processed by the node shall be treated as if the security operation has been represented by a single BCB with a single security operation.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This helps for the purposes of report generation and policy processing.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when the inspection of thecode shows that if the BCB data structure contains multiple securityoperations, each operation processed by the node shall be treated as ifthe security operation has been represented by a single BCB with a singlesecurity operation.</td></tr></table>

## BPSec-045 Receiving BIBs 1

When a received bundle contains a BIB, the receiving node shall determine whether it is the security acceptor for any of the security operations in the BIB.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This check is needed to determine the steps to process the bundle.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that for a received bundle by HDTN ingress module with a BIB,there&#x27;s a check in the code to determine whether the node is the securityacceptor for any of the security operations in the BIB.</td></tr></table>

## BPSec-046 Receiving BIBs 2

When the receiving node is the security acceptor for any of security operations in a BIB:

1. The node shall process those operations.

2. Remove any operation specific information from the BIB prior to forwarding the bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is because the acceptor does the final processing of the securityoperation.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that If thereceiving node is configured as the security acceptor for any securityoperations in a BIB, the node successfully processes those operationsand removes any operation specific information from the BIB prior todelivering data to an application at the node or forwarding the bundle.</td></tr></table>

## BPSec-047 Receiving BIBs 3

BPSec shall process the targets according to the security policy following an integrity security operation failure.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>In case of security operation failure, the action for target processing isbased on the security policy configured by the user.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that whenreceiving a bundle with BIB and if the processing a security operationfails, the target is processed according to the security policy in the BPSecconfig file.</td></tr></table>

## BPSec-048 Receiving BIBs 4

BPSec shall generate a bundle status report to indicate an integrity security operation failure.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>In case of security operation failure, a bundle status report generation willhelp for debugging and tracking these failures.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that whenreceiving a bundle with BIB and if processing of a security operation fails,a bundle status report indicating the failure is generated.</td></tr></table>

## BPSec-049 Receiving BIBs 5

When BPSec removes all the security operations for a given BIB, that BIB shall be removed from the bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is the final stage in the security operation lifecycle and that BIB is notneeded anymore.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that whenall security operations for a BIB have been removed from the BIB, the BIBis removed from the bundle.</td></tr></table>

## BPSec-050 Receiving BIBs 6

BPSec shall process a BIB only if the security target of the BIB is not the security target of a BCB in the bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>When both a BIB and a BCB share a security target, it means that thesecurity target must have been encrypted after it was integrity signed;therefore, the BIB cannot be verified until the security target has beendecrypted by processing the BCB.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows with abundle where both a BIB and a BCB share a security target, that BIB isnot processed until the security target has been decrypted by processingthe BCB.</td></tr></table>

## BPSec-051 Receiving BIBs 7

When the security policy of a node requires a node to apply integrity to a specific security target and no such BIB is present in the bundle, the node shall process this security target in accordance with the security policy.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>We shall process the BIB based on the configured security policy.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when we emulate a testwhere the security policy of a node specifies a node should have appliedintegrity to a specific security target but no such BIB is present in thebundle, it results in the node processing this security target as configuredin the BPSec config file.</td></tr></table>

## BPSec-052 Receiving BIBs 8

When the security policy of a node specifies a node should have applied integrity to a specific security target and no such BIB is present in the bundle, the node shall remove the security target from the bundle when the security target is not the payload or primary block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is considered an integrity security failure and security target could becompromised and should be removed. The payload and primary blocksare required in a bundle and cannot be removed.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that if thesecurity policy of a node specifies a node should have applied integrity toa specific security target and no such BIB is present in the bundle, thenode removes the security target from the bundle as long as the securitytarget is not the payload or primary block.</td></tr></table>

## BPSec-053 Receiving BIBs 9

When the target block of the failed integrity security operation is the primary block, BPSec shall discard the bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The primary block is required in a bundle and cannot be discarded</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test with an integritysecurity operation targeting the primary block fails, the bundle isdiscarded.</td></tr></table>

## BPSec-054 Receiving BIBs 10

When the target block of the failed integrity security operation is the payload block, BPSec shall discard the bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The payload block is required in a bundle and cannot be discarded.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test with an integritysecurity operation targeting the payload block fails, the bundle isdiscarded.</td></tr></table>

## BPSec-055 Receiving BIBs 11

When a receiving node is not the security acceptor of a security operation in a BIB, the node shall attempt to verify the security operation.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is to prevent forwarding corrupt data.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that whena node is the security verifier of a security operation in a BIB, the nodeattempts to verify the security operation.</td></tr></table>

## BPSec-056 Receiving BIBs 12

When a verification security operation fails, the node shall process the security target in accordance with local security policy.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>In case of security operation failure the action for target processing isbased on the security policy configured by the user.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that ifthere&#x27;s a BIB security operation failure, the node processes the securitytarget in accordance with security policy configured in the BPSec configfile.</td></tr></table>

## BPSec-057 Receiving BIBs 13

When a payload integrity check fails at a waypoint, BPSec shall trigger a failure of a payload integrity check at the bundle destination.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The waypoint shall verify the security operation and prevent forwardingcorrupt data.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that if apayload integrity check fails at a waypoint node, the payload is processedas a failure of a payload integrity check at the bundle destination.</td></tr></table>

## BPSec-058 Receiving BIBs 14

When a BIB integrity check passes at a waypoint, the node shall retain the security operation in the BIB prior to forwarding.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>If the integrity check passes at the waypoint, the bundle is verified andshould be forwarded to the next hop. Only the acceptor removes the BIBextension block.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that if aBIB integrity check passes at a waypoint, the node will retain the securityoperation in the BIB prior to forwarding.</td></tr></table>

## BPSec-059 Receiving BIBs 15

When a BIB contains multiple security operations, each operation processed by the node shall be treated as if the security operation has been represented by a single BIB with a single security operation.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is for the purposes of report generation and policy processing.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when the inspection of thecode shows that if the BIB data structure contains multiple securityoperations, each operation processed by the node shall be treated as ifthe security operation has been represented by a single BIB with a singlesecurity operation.</td></tr></table>

## BPSec-060 Bundle Fragmentation and Reassembly

When fragmentation is required for a bundle payload, and BPSec has applied security services to that bundle, BPSec shall only fragment the payload block.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is because security blocks, like all extension blocks, can never befragmented.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>NA - HDTN Bundle fragmentation for BPv7 is not implemented at thistime. This will be added soon.</td></tr></table>

## BPSec-061 BIB and BCB Blocks Addition to a Bundle

BPSec shall prevent the addition of BCB or BIB to a bundle if the ‘Bundle is a fragment’ flag is set to true in the bundle processing control flags field.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9172 Section 5.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is because fragmentation delays certain security processing untilbundle reassembly, which results in some extension blocks beingduplicated, and the result of security failures being ambiguous in thepresence of fragmentation.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when BIB or BCB are notallowed to be added to a bundle if the &quot;Bundle is a fragment&quot; flag set -HDTN Bundle fragmentation for BPv7 is not implemented at this time.This will be added soon.</td></tr></table>

## 4 ROUTING REQUIREMENTS

## Routing-001 Contact Plan Modification

All route lists shall be recomputed when the contact plan has been modified.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>SABR 3.2.3.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Contact plan changes may invalidate any or all earlier route computations.When the contact plan is updated, new routes are calculated.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is performedthat updates the HDTN contact plan and confirms the route list has beenrecomputed.</td></tr></table>

## Routing-002 Expired Contacts

Expired contacts shall be deleted from the contact graphs.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>SABR 3.2.3.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>These contacts have exceeded their defined period of validity and are nolonger used.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is performedthat loads a contact plan with expired contacts into HDTN and confirmsthe expired contacts have been removed from the contact plan.</td></tr></table>

## Routing-003 Route Computation

The route with the earliest arrival time shall be selected from the list of candidate routes.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>SABR 3.2.4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Both CGR and CMR use the earliest time of arrival to select the bestroute.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is performedthat loads a contact plan into HDTN and verifies the route with the earliestarrival time has been selected from the list of candidate routes.</td></tr></table>

## Routing-004 CGR Preparation

The list of candidate routes shall be computed from the contact plan.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>SABR 3.2.5</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The contact plan is the schedule of contacts for each node. It is the inputto the router. The list of candidate routes is computed for each finaldestination based on the root contact, final destination, and contact startand stop times. All routes are computed in order to select the best.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is performedthat loads a contact plan into HDTN and verifies the computed candidateroutes match the expected values.</td></tr></table>

## Routing-005 Routing Algorithm Selection

The routing algorithm shall be selected from one of the following: contact graph routing or contact multigraph routing.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>NA</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>HDTN is intended to support multiple routing algorithms including CGR,CMR, and others. The algorithm is selected by the user.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when an inspection of thecode shows that CGR and CMR are both supported as routing algorithms.</td></tr></table>

## Routing-006 Rerouting Around Failed Node

The router shall select the route with the next earliest arrival time if it detects that the current route has failed.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>NA</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>All routes have been precomputed so that if the current route fails, thenext best route can be used.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is performedthat simulates a route failure on the selected route and confirms thatHDTN selects a new route.</td></tr></table>

## 5 TCPCL REQUIREMENTS

## TCPCL-001 Network Byte Order

The integer encodings shall transmit in network byte order.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 2.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is the byte order for integers per RFC 9174. Big endian byte orderingis the same as network byte order. This means the bits are transmitted inthis order: bits 0-7 first, then bits 8-15, then 16-23 and bits 24-31 last.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test shows thatinteger encodings are received in network byte order.</td></tr></table>

## TCPCL-002 Session Establishment

When using TCPCL for bundle transmissions, communicating entities shall establish a TCPCL session.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>TCPCL requires a handshake with the other node to make certain bothsides are compatible for transmission and reception.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test and inspection onWireshark show two TCPCL nodes establishing a session andexchanging data successfully.</td></tr></table>

## TCPCL-003 Contact Header

To establish a TCP connection, the active entity shall transmit its Contact Header.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The contact header of TCPCL contains the required pieces for the twonodes to attach. Without sending the contact header, then nocommunication/handshake can partake.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified after a test is performedshowing the active entity transmitting its Contact Header.</td></tr></table>

## TCPCL-004 Contact Header Reception

When the passive entity receives the Contact Header of an active entity, then the passive entity shall transmit its Contact Header.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>To complete a handshake, the passive/receiver node must acknowledgereception of the active/transmitter node&#x27;s contact header by sending outthe passive node&#x27;s contact header. By checking each node&#x27;s contactheader, each node is able to make certain a communication can be made.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test and inspection onWireshark show that the passive entity transmitting its Contact Headerafter receiving the active entity&#x27;s Contact Header.</td></tr></table>

## TCPCL-005 TCP Idle Timeout

The TCP connection shall close when the entity timer matches the specified timeout waiting time.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Timeouts avoid an idle network. Timeouts ensure the network will not be&#x27;hung up&#x27; in any particular node.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that assoon as the timeout timer is reached the TCP connection closes.</td></tr></table>

## TCPCL-006 TCP FIN

The entity shall use the TCP FIN mechanism when closing a TCP connection.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>There are two mechanisms within TCP for opening and closingconnections: RST and FIN. FIN is the standard clean close for a TCPconnection.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when an entity is closing aTCP connection uses the TCP FIN mechanism.</td></tr></table>

## TCPCL-007 Enable TLS by CAN\_TLS Flag

TLS shall change the CAN\_TLS flag within its Contact Header to 1 when enabled.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>TLS is designed to facilitate privacy and data security for communicationsover the network. CAN_TLS indicates that the sending peer has enabledTLS security. It is recommended to enable TLS for all sessions.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that TLS isenabled by setting the following fields in the HDTN outduct config:tryUseTIs, tIsIsRequired, useTIsVersion1_3 or useTIsVersion1_4,doX509CertificateVerification, verifySubjectAltNamelnX509Certificate,certificationAuthorityPemFileForVerification.</td></tr></table>

## TCPCL-008 Magic String Validation

The connection shall terminate when the "dtn!" string is not present in the contact header.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.3</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Magic is a four-octet field that always contains the octet sequence 0x640x74 0x6E 0x21, i.e., the text string &quot;dtn!&quot; in US-ASCII (and UTF-8). Magicis one of the 3 fields within a TCP contact header.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows, that uponreceiving a message without the &quot;dtn!&quot; string in its contact header, thereceiving entity terminates the connection.</td></tr></table>

## TCPCL-009 Version Number Negotiation

The active entity shall terminate the TCP connection when the passive entity's TCPCL protocol version is lower than the active entity's version provided in the Contact Header.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.3</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Both Contact Headers of a successful contact negotiation must haveidentical TCPCL version numbers. TCPCL versions are not backwardsand forwards compatible.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that theactive entity terminates the TCP connection when the active entityreceives a TCPCL protocol version lower than its version provided in theContact Header.</td></tr></table>

## TCPCL-010 Reattempt Failed Connections

Failed connection attempts shall use a (binary) exponential backoff mechanism to increase the delay between retries in the case of repeated failures.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The TCPCL entity should not overwhelm its target with repeatedconnection attempts.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that the backoff mechanism increases the delay between retriesvia a binary exponential when there are failed connection attempts.</td></tr></table>

## TCPCL-011 Version Mismatch Reason Code

When the active entity terminates the TCP connection from TCPCL protocol version mismatch, then the passive entity shall terminate the TCP connection with a reason code of "Version Mismatch".

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.3</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Both Contact Headers of a successful contact negotiation must haveidentical TCPCL version numbers. TCPCL versions are not backwardsand forwards compatible.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that the active entity terminated the TCP connection from versionmismatch with a reason code of &quot;Version Mismatch&quot; when the TCPCLprotocol version in the contact header is not supported.</td></tr></table>

## TCPCL-012 TLS Lifetime

The lifetime of the underlying TCP connection shall match the lifetime of a TLS connection.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>When the TCP connection is terminated, then the TLS connection will alsobe terminated. This is because TLS resides on the TCP connection whenit is enabled.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test with TLS enabledshows that the lifetime of the underlying TCP connection matches thelifetime of the TLS connection during the handshake.</td></tr></table>

## TCPCL-013 Node ID Matching

The implementation shall terminate the session when a contact header contains a NODE-ID that does not match the URI "ipn:nextHopNodeId.0".

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>ION 3.7.2 source code tcpcli.c line 1199 uses service number 0 forcontact header. Therefore for SSL verification, implementations need todo a string compare of &quot;ipn:nextHopNodeld.0&quot;. This is for compatibilitybetween network implementations. If the validation result fails or if theresult is absent and the security policy requires an authenticated node IDthen the session will terminate (reason code: &quot;Contact Failure&quot;).</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test proving that theentity will terminate the session when a contact header is received withoutthe URI &quot;ipn:nextHopNosdeld.0&quot;.</td></tr></table>

## TCPCL-014 Certificate Profile

End-entity certificates used by a TCPCL entity shall conform to RFC 5280, or any updates or successors to that profile.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.4.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Certificates need to interoperable with other entities and therefore need toconform to those certificate profiles.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a code inspectionshows that the TCPCL end-entity certificates conform to RFC 5280.</td></tr></table>

## TCPCL-015 Version 3 Certificates

TCPCL shall require TCPCL version 3 certificates.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.4.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The TCPCL requires version 3 certificates due to the extensions used bythe TCPCL certificate profile. It will reject version 1 and version 2 end-entity certificates.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is providedshowing TCPCL version 3 certificates are used.</td></tr></table>

## TCPCL-016 Node ID Certificate

The TCPCL end-entity certificate shall contain a NODE-ID when applicable by CA policy.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.4.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>When assigned one or more stable DNS names, a TCPCL end-entitycertificate contain a DNS-ID that authenticates those (fully qualified)names. When assigned one or more stable network addresses, a TCPCLend-entity certificate contains an IPADDR-ID that authenticates thoseaddresses.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test shows a TCPCLend-entity certificate containing a NODE-ID when CA policy is enabled.</td></tr></table>

## TCPCL-017 Type-ID

The active entity shall terminate the session if the type-id id-on-bundleEID does not match the passive entity's next hop endpoint ID.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.4.2.1.</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Network integrity is lost when messages are delivered to the wrong node.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a bundle with a badcertificate is sent and is rejected at the receiving node.</td></tr></table>

## TCPCL-018 TLS Authentication

The requested TLS handshake shall perform the TLS authentication.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.4.4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>It is recommended to enable TLS for all sessions. TLS designed tofacilitate privacy and data security for communications over the network.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that the TLS authentication happens during the TLS handshake.</td></tr></table>

## TCPCL-019 Node ID Mismatch

When the active entity's SESS\_INIT received differs from the intended node ID, the TCPCL session shall reject the SESS\_INIT.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Network integrity is lost when messages are delivered to the wrong node.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test and bundleinspection on Wireshark show that the active entity&#x27;s SESS INIT receivedmatches intended node ID and the SESS_INT is rejected if the two do notmatch.</td></tr></table>

## TCPCL-020 Transfer MRU

When the Transfer MRU provided during negotiation is unacceptable, the entity shall terminate the session with a reason code of "Contact Failure”.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.7</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Reason codes enable network statistics. These statistics can be used tounderstand how the network is operating.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a code inspectionshows a termination and reason code of &quot;Contact Failure&quot; happens whenthe Transfer MRU is unacceptable.</td></tr></table>

## TCPCL-021 Segment MRU Contact Failure

When the Segment MRU provided during negotiation is unacceptable, the entity shall terminate the session with a reason code of "Contact Failure".

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.7</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Reason codes enable network statistics. These statistics can be used tounderstand how the network is operating.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a code inspectionshows a termination and reason code of &quot;Contact Failure&quot; happens whenthe Segment MRU is unacceptable.</td></tr></table>

## TCPCL-022 Session Keep-alive Interval

When the Session keep-alive Interval provided during negotiation is unacceptable, the entity shall terminate the session with a reason code of "Contact Failure".

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.7</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Nodes require proper keep-alive intervals and timeouts, so nodes are not&quot;hung up&quot;.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows a contactheader being sent that has a bogus keep-alive interval and the receivingentity terminates the session with a reason code of &quot;Contact Failure&quot;.</td></tr></table>

## TCPCL-023 Session Extension Items Contact Failure

When a TCPCL entity receives a Session Extension Items Item Flags with an unknown Item Type and the CRITICAL flag is 1, the entity shall refuse the TCPCL session with a SESS\_TERM reason code of "Contact Failure".

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Reason codes enable network statistics. These statistics can be used tounderstand how the network is operating.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test shows a TCPCLentity receiving a Session Extension Items Item Flags with an unknownItem Type and the CRITICAL flag = 1 and the entity refusing the TCPCLsession with a SESS TERM reason code of &quot;Contact Failure&quot;.</td></tr></table>

## TCPCL-024 Session Extension Items Encoding

Session Extension Items shall use Type-Length-Value (TLV) containers encoding.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 4.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is a requirement from RFC 9174 section 4.8. The fields of SessionExtension Items are: item flags, item type, item length, and item value.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a code inspectionshows Session Extension Items encoded as TLV containers.</td></tr></table>

## TCPCL-025 Keep-alive

Nodes shall send a keep-alive message when no message transmission reception happens during the negotiated interval.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Timeouts avoid an idle network. Timeouts ensure the network will not be&#x27;hung up&#x27; in any particular node. Keep-alive messages are the network&#x27;slast chance before a timeout occurs.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test shows an entitysending a keep-alive message when no message transmission receptionhappens during the negotiated interval between entities.</td></tr></table>

## TCPCL-026 SESS\_TERM Idle Timeout

The entity shall terminate the session by transmitting a SESS\_TERM message with a reason code of "Idle timeout" when no message transmission reception happens during the negotiated interval.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.1.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Messages can be keep-alive or other. Reason codes enable networkstatistics. These statistics can be used to understand how the network isoperating.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows an entity terminating the TCP connection from no messagetransmission reception during the negotiated interval with a reason codeof &quot;Idle timeout&quot;.</td></tr></table>

## TCPCL-027 Message Unsupported

When a TCPCL entity receives a known message type but is inappropriate for the negotiated session parameters, the entity shall send a MSG\_REJECT message with a reason code of "Message Unsupported".

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is a catch statement. An inappropriate message can bedue to an incorrectly negotiated session extension. Reason codes enablenetwork statistics. These statistics can be used to understand how thenetwork is operating.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows an entity sending a MSG_REJECT message from a wrongmessage type for the negotiated session parameters with a reason codeof &quot;Message Unsupported&quot;.</td></tr></table>

## TCPCL-028 Message Unexpected

When a TCPCL entity receives a message that is inappropriate for the current session state, the entity shall send a MSG\_REJECT message with a reason code of "Message Unexpected".

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.1.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Inappropriate for the current session state can mean a SESS_INIT afterthe session has already been established or a XFER_ACK message withan unknown Transfer ID</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows an entitysending a MSG_REJECT message with a reason code of &quot;MessageUnsupported&quot; when it was sent a known message type that did not makesense for the negotiated session parameters.</td></tr></table>

## TCPCL-029 TCPCL Segment to Segment MRU

A TCPCL segment shall be less than or equal to the receiving entity's Segment MRU.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>A receiving entity can set the Segment Maximum Receive Unit (MRU) inits SESS_iNIT message to determine the largest acceptable segmentsize, and a transmitting entity can segment a transfer into any sizessmaller than the receiver&#x27;s Segment MRU. It is a network administrationmatter to determine an appropriate segmentation policy for entities usingthe TCPCL protocol.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows the comparison of a TCPCL segment is less than or equal to thereceiving entity&#x27;s Segment MRU.</td></tr></table>

## TCPCL-030 Single Transfer

A single transfer shall contain a single bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is imposed on the agent using the TCPCL, rather thanon the TCPCL itself. Data must be as one unit since TCPCL is unable tohandle fragmentation like the bundle protocol layer.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a Wireshark test showsthat a single bundle is always captured in a single TCP transfer.</td></tr></table>

## TCPCL-031 Multiple Bundles

Multiple bundles on a single TCPCL connection shall transmit contiguously.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is a requirement from RFC 9174 section 5.2. Transmitting multiplebundles contiguously aids the network by not losing a bundle.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a Wireshark test showsthat a single TCPCL connection transmits contiguously when there aremultiple bundles being sent.</td></tr></table>

## TCPCL-032 Unique Transfer ID

Transfer IDs shall differ between endpoint entities within a single TCPCL session and direction.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>When transfer IDs are not unique within a single TCPCL session thencommunications could be accepted at another node. When this happens,the network will lose its validity and integrity.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test of multiplebundles within a single TCPCL session contains different transfer IDsbetween endpoint entities.</td></tr></table>

## TCPCL-033 Reserved Message Header Flag Set

The sender shall set the reserved message header flag bits to 0.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Reserved message header flag bits are found within the Contact Header.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows thesender&#x27;s reserved message header flag bits are zero.</td></tr></table>

## TCPCL-034 Transfer Extension Items Length

The Transfer Extension Items Length and Transfer Extension Items list shall only be present when the START flag is 1 on the message.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Transfer Extension Items Length and Transfer Extension Items list:Together, these fields represent protocol extension data for thisspecification.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows theTransfer Extension Items Length and Transfer Extension Items arepresent when the START = 1 on the message and a test showing that theTransfer Extension Items Length and Transfer Extension Items list areNOT present when the START = 0.</td></tr></table>

## TCPCL-035 START Flag

The first segment of a transfer shall set the START flag = 1.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The flags portion of the message contains two flag values in the two low-order bits, denoted START and END in XFER SEGMENT flags. Theseflags are to start and stop a handshake.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test shows the firstsegment of a transfer contains START = 1 and END = 0.</td></tr></table>

## TCPCL-036 END Flag

The last segment of a transfer shall set the END flag = 1.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The flags portion of the message contains two flag values in the two low-order bits, denoted START and END in XFER SEGMENT flags. Theseflags are to start and stop a handshake.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test shows the lastsegment of a transfer contains START = 0 and END = 1.</td></tr></table>

## TCPCL-037 Bundle Transfer

When a transfer of a bundle has commenced, the entity shall only send segments containing sequential portions of that bundle to the END flag = 1 segment.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The flags portion of the message contains two flag values in the two low-order bits, denoted START and END in XFER_SEGMENT flags. Theseflags are to start and stop a handshake.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows thatinterleaving of multiple transfers from the same entity is not possiblewithin a single TCPCL session.</td></tr></table>

## TCPCL-038 Transfer ACK

A receiving TCPCL entity shall send XFER\_ACK message(s) in response to receiving processed XFER\_SEGMENT message segment(s).

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.3</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The rationale behind these acknowledgments is to enable the transmittingentity to determine how much of the bundle has been received, so that ifthe session is interrupted, it can perform reactive fragmentation to avoidresending the already transmitted part of the bundle. In addition, there isno explicit flow control on the TCPCL.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test shows areceiving TCPCL entity sending XFER_ACK messages in response to thesame amount of receiving processed XFER_SEGMENT messagesegments.</td></tr></table>

## TCPCL-039 XFER\_ACK Flags

The flags portion of the XFER\_ACK header shall match the acknowledged corresponding XFER\_SEGMENT message.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.3</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The flags portion include flags that are not decodable to the entity. Therationale behind these acknowledgments is to enable the transmittingentity to determine how much of the bundle has been received, so that ifthe session is interrupted, it can perform reactive fragmentation to avoidresending the already transmitted part of the bundle. In addition, there isno explicit flow control on the TCPCL.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test shows the flagsportion of the XFER_ACK header matches the same number of receivingprocessed XFER_SEGMENT message segments.</td></tr></table>

## TCPCL-040 Transfer Refuse ID

The transfer sender shall indicate the transfer ID of a refused transfer.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>By indicating the transfer ID of a refused transfer, the network statics canaid the overall network health including the health of each individual node.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test shows that thetransfer sender indicates the transfer ID of a refused transfer that wassent.</td></tr></table>

## TCPCL-041 Complete Transmission

When a sender receives a XFER\_REFUSE message, the sender shall complete the transmission of partially sent XFER\_SEGMENT message(s).

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This handshake lets the sender know what was received.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test shows a sendercompleting its transmission of partially sent XFER_SEGMENT messagesafter receiving a XFER_REFUSE message.</td></tr></table>

## TCPCL-042 Refused Bundle XFER\_REFUSE

Subsequent segments of a refused bundle shall be refused with a XFER\_REFUSE message.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>For network management purposes it is important to label all parts of themessage so if a segment is received the receiving entity knows what itshould do.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that itlabels all subsequent segments of a refused bundle with aXFER_REFUSE message.</td></tr></table>

## TCPCL-043 Transfer Extension Items

Transfer Extension Items shall use Type-Length-Value (TLV) containers encoding.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.5</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Transfer Extension Items are defined in RFC 9174 section 5.2.5. TransferExtension item fields are: item flags, item type, item length, and itemvalue.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a code inspectionshows Transfer Extension Items encoded as TLV containers.</td></tr></table>

## TCPCL-044 CRITICAL Flag 1

When a TCPCL entity receives a Transfer Extension Item with an unknown Item Type and the CRITICAL flag is 1, then the entity shall refuse the transfer with a XFER\_REFUSE reason code of "Extension Failure".

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.5</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Reason codes enable network statistics. These statistics can be used tounderstand how the network is operating.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test shows a TCPCLentity receiving a Transfer Extension Item with an unknown Item Type andthe CRITICAL flag = 1 and the entity refusing the transfer with aXFER REFUSE reason code of &quot;Extension Failure&quot;.</td></tr></table>

## TCPCL-045 Single Transfer Length Extension Items

At the start of a bundle, a transfer that contains segments shall contain a single Transfer Length Extension Item.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.5</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This requirement is imposed on the agent using the TCPCL, rather thanon the TCPCL itself.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test showing abundle transfer with multiple segments contains a single Transfer LengthExtension Item.</td></tr></table>

## TCPCL-046 IANA Code Point

The Transfer Length Extension shall use the IANA-assigned code point.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.5</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>IANA has created the &quot;Bundle Protocol TCP Convergence-Layer Version4 Transfer Extension Types&quot; registry and populated it with the contents ofthe Transfer Length Extension Codes. Values in the range 0x8000-0xFFFF are reserved for Private or Experimental Use, which are notrecorded by IANA.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows the Transfer Length Extension value is assigned by the lANA-assigned code point options.</td></tr></table>

## TCPCL-047 Total Length Field

The receiver shall accept a received bundle when the Total Length value matches the length of the bundle data received.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.5</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The total length mandates what the length is going to be. The authoritythat the receiver has is to accept it or not.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows a receivedbundle being accepted based on the Total Length value matching thelength of the bundle data received.</td></tr></table>

## TCPCL-048 Actual Total Length

When the actual total length of bundle data received is different from the value indicated by the Total Length value, then the receiver shall:

1. Invalidate the transmitted data.

2. Send a XFER\_REFUSE with a reason code of "Not Acceptable".

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 5.2.5</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Reason codes enable network statistics. These statistics can be used tounderstand how the network is operating.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows a receiverinvalidating transmitted data and sending a XFER_REFUSE messagewith a reason code of &quot;Not Acceptable&quot; when the actual total length ofbundle data received is different from the value indicated by the TotalLength value.</td></tr></table>

## TCPCL-049 Session Termination

To terminate a session, an entity shall

1. Complete transmission of other message(s).

2. Transmit a SESS\_TERM message.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 6.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Must finish the handshake for both parties to terminate the session.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is performedshowing one entity terminating a session (by SESS_TERM message) andthe other entity completing transmission of its message and transmittingits SESS_TERM message.</td></tr></table>

## TCPCL-050 SESS\_TERM Message

When initiating a termination, the REPLY flag of a SESS\_TERM message shall be set to 0.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 6.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Setting the REPLY flag of a SESS_TERM message lets the other nodeknow that its connection wants to have a clean close out.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test shows an entityterminating a session by sending the REPLY = 0 in a SESS_TERMmessage and a test showing that an entity with REPLY = 1 in aSESS_TERM message does not terminate the session.</td></tr></table>

## TCPCL-051 Acknowledging SESS\_TERM

Upon receiving an initial SESS\_TERM message in the current session, an entity shall send an acknowledging SESS\_TERM message.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 6.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The receiver node must acknowledge the sender to complete ahandshake.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test shows that areceiving SESS_TERM message entity, sends its acknowledgingSESS_TERM message.</td></tr></table>

## TCPCL-052 XFER\_REFUSE

While the Ending state attempts a new incoming transfer, the receiving entity shall send a XFER\_REFUSE with a reason code of "Session Terminating".

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 6.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Reason codes enable network statistics. These statistics can be used tounderstand how the network is operating.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows an entity sending a XFER_REFUSE message from being in anEnding state with a reason code of &quot;Session Terminating&quot;.</td></tr></table>

## TCPCL-053 TCP Closed Failed Transfer

When the underlying TCP connection closes during a transmission, the BPA shall indicate the failed transfer.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 6.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>TCP connections can be closed in either transfer stream.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when HDTN receives an errormessage that the TCP socket is closed when the underlying TCPconnection is closed.</td></tr></table>

## TCPCL-054 Contact Header Fails TCP Closes

When reception of the Contact Header fails, an entity shall close the TCP connection without sending a SESS\_TERM message.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 6.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Contact Header is sent first to make certain the two nodes are compatible.The SESS_TERM message sets the final settings of the communication.A reception of the contact header can fail by receiving an invalid magicstring.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows an entityclosing the TCP connection without sending a SESS_TERM messageafter it received a failed Contact Header.</td></tr></table>

## TCPCL-055 Ending State

While the session is in the Ending state, an entity shall complete the termination transfer procedure for the remainder of the session.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 9174 Section 6.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>When the handshake/session is in the termination process, the two nodesare focused on a clean close-out. Therefore, no new transmission andreceiver messages are able to be handled.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that whena session is in the ending state, no new incoming and outgoing transfersare ignored.</td></tr></table>

## 6 STCP REQUIREMENTS

## STCP-001 Bundle Reception

Bundles shall be received over the connected TCP socket.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>STCPCLI</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>STCPCL was implemented for compatibility with ION.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is performedthat initializes an STCPCL outduct and confirms a TCP connection is usedas the protocol for bundle transfer.</td></tr></table>

## STCP-002 Bundle Reception Length

STCP shall interpret a 32-bit unsigned integer preceding a bundle in network byte order as the length of the bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>STCPCLI</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The 32-bit length frames the bundle within a TCP stream.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is performedthat sends a bundle to an STCPCL induct and confirms the initial 32-bitinteger of the bundle is read as the bundle length and is used to read thecorrect number of bytes from the TCP stream.</td></tr></table>

## STCP-003 Unidirectional Link

Each STCPCL link shall be unidirectional.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>STCPCL</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The next hop node ID is unknown,</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when each STCP link hasbeen shown to be unidirectional.</td></tr></table>

## STCP-004 Bundle Transmission

Bundles shall be transmitted over the connected TCP socket.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>STCPCLO</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>STCP was implemented for compatibility with ION.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when bundles aretransmitted over the TCP connection.</td></tr></table>

## STCP-005 Bundle Transmission Length

Bundles transmitted on the connection shall be preceded by a 32−bit unsigned integer in network byte order indicating the length of the bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>STCPCLO</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The 32-bit length frames the bundle within a TCP stream.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is performedthat receives a bundle from an STCPCL outduct and confirms the value ofthe 32-bit integer preceding the bundle matches the length of the bundle.</td></tr></table>

## STCP-006 STCPCL Keep-alive

Keep-alive packets shall be indicated by a 32-bit unsigned integer with all bits set to zero.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>STCPCL</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Keep-alive packets have been implemented for compatibility with IONSTCPCL.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is performedthat monitors an STCPCL outduct and confirms the TCP session ismaintained by periodic reception of data or 32-bit unsigned integer with allbits set to zero.</td></tr></table>

## STCP-007 STCPCL Keep-alive Interval

Keep-alive packets shall be transmitted at a user specified interval when no data is being transmitted.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>STCPCL</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Keep-alive packets have been implemented for compatibility with IONSTCPCL.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is performedthat monitors an STCPCL outduct and confirms keep-alives aretransmitted at the user specified interval.</td></tr></table>

## STCP-008 Maximum Bundle Length

Accepted bundles shall be less than or equal to a user specified maximum length.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>STCPCLI</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Very large bundles could consume a large amount of memory.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is performedthat sends an oversized bundle to an STCPCL induct and confirms theconnection is terminated.</td></tr></table>

## 7 UDP REQUIREMENTS

## UDPCL-001 BP Over a Datagram CL

A UDP datagram shall contain one bundle.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>UDP RFC 7122 Section 3.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>In order to utilize DTN protocols across the Internet, it is necessary toencapsulate them into a standard Internet Protocol so that they traveleasily across the Internet. UDP is a unidirectional protocol with nocongestion control. One bundle per datagram simplifies the convergencelayer.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is performedthat receives a datagram from a UDPCL outduct and confirms thedatagram contains exactly one bundle.</td></tr></table>

## UDPCL-002 UDP Keep-alive

UDPCL inducts shall interpret receiving 4 octets of zero bits as a keep-alive.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>UDP RFC 7122 Section 3.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>UDPCL inducts support receiving keep-alives for compatibility with otherimplementations.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when inducts accept 4octets of zero bits as keep-alives, does not log an error, and does notattempt to deliver them as data.</td></tr></table>

## UDPCL-003 Bundle Fragmentation

Bundles shall be fragmented into UDP datagrams based on a configured MTU.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>UDP RFC 7122 Section 3.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Bundles that are too large for the path MTU shall be fragmented andreassembled to prevent IP fragmentation.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when bundles arefragmented into UDP datagrams that match the configured MTU size.</td></tr></table>

## UDPCL-004 Rate Limit

UDP outduct transmission rates shall be limited by a user specific rate limit.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>UDP RFC 7122 Section 3.6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>UDP packets will be dropped if they exceed the expected link rate.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is performedthat receives data from a UDPCL outduct and confirms the received datarate does not exceed the configured rate.</td></tr></table>

## UDPCL-005 Port Configuration Listening

UDP induct shall bind to an user provided port.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>UDP RFC 7122 Section 3.2.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>UDP connections are to be established via a known port.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is performedthat connects successfully to an UDPCL induct utilizing the expected port.</td></tr></table>

## UDPCL-006 Port Configuration Transmission

UDP outduct shall connect to an user provided port.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>UDP RFC 7122 Section 3.2.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>UDP connections are to be established via a known port.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement shall be considered verified when a test is performedthat receives a connection from an UDPCL outduct utilizing the expectedport.</td></tr></table>

## 8 LTP REQUIREMENTS

## LTP-001 Session ID

A session ID shall consist of the engine ID of the sender and a session number randomly generated by the sender.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 3.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is the definition of the session ID.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that aseries of session IDs consists of the engine ID of the sender and asession number randomly generated by the sender.</td></tr></table>

## LTP-002 Unique Session ID

Every session initiated by an LTP engine shall be uniquely identified by a session ID.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 3.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Each session needs a unique ID to distinguish it from other sessions.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that aseries of bundles transmitted from an LTP outduct contains uniquesession IDs.</td></tr></table>

## LTP-003 Incrementing Checkpoint Serial Numbers

Any subsequent checkpoints issued by the sender shall have the serial number value found by incrementing the prior checkpoint serial number by 1.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 3.2.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>The checkpoint serial number uniquely identifies the checkpoint among allcheckpoints issued by the block sender in a session.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that aseries of checkpoint serial numbers increment by one for eachsubsequent checkpoint.</td></tr></table>

## LTP-004 Retransmitted Checkpoints

When a checkpoint segment is retransmitted, its serial number shall be the same as when it was originally transmitted.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 3.2.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Retransmitted serial numbers should not be changed from the originalserial number since it is related to the same checkpoint</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that theserial number for a retransmitted checkpoint is the same as the serialnumber of the original checkpoint.</td></tr></table>

## LTP-005 Report Serial Number

When the checkpoint is queued for transmission in response to the reception of an RS, then its value shall be the report serial number value of the RS that caused the data segment to be queued for transmission.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 3.2.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>This is required according to section 6.13 of RFC 5326.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that thereport serial number of a received RS matches the RS that caused thedata segment to be queued for transmission.</td></tr></table>

## LTP-006 Report Segment

Any subsequent Report Segment issued by the receiver shall have the serial number value found by incrementing the last report serial number by 1.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 3.2.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 3.2.2 and helps ensureinteroperability with other DTNs.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that aseries of Report Segments have a report serial number that incrementsby 1.</td></tr></table>

## LTP-007 Retransmitted Report Segment

When a Report Segment is retransmitted, its serial number shall be the same as when it was originally transmitted.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 3.2.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 3.2.2 and helps ensureinteroperability with other DTNs.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that aretransmitted Report Segment contains its original serial number.</td></tr></table>

## LTP-008 Report Serial Number Greater Than Zero

The report serial number shall be greater than zero.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 3.2.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 3.2.2 and helps ensureinteroperability with other DTNs.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that the report serial number disallows zero.</td></tr></table>

## LTP-009 Checkpoint Serial Number

The value of the checkpoint serial number shall be zero if the report segment is not a response to reception of a checkpoint.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 3.2.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 3.2.2 and it&#x27;s used todifferentiate from a response to reception of a checkpoint.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Needs further discussion.</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>Draft requirement. Needs further discussion.</td></tr></table>

## LTP-010 Checkpoint Serial Number RS

The value of the checkpoint serial number shall be the checkpoint serial number of the checkpoint that caused the RS to be issued if the report segment is a response to reception of a checkpoint.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Draft</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 3.2.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 3.2.2 and it&#x27;s used todifferentiate from a response to reception of a checkpoint.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Needs further discussion.</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>Draft requirement. Needs further discussion.</td></tr></table>

## LTP-011 Reception Claims Length Limits

The sum of an LTP Reception Claim's length and offset shall not exceed the difference between the upper and lower bounds of the report segment.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 3.2.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 3.2.2.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that thesum of à LTP Reception Claim&#x27;s length and offset is between the upperand lower bounds of the report segment.</td></tr></table>

## LTP-012 Reception Claims Offset

An LTP Reception Claim's offset shall be greater than the sum of the offset and the length of the prior claim.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 3.2.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 3.2.2.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that a LTPReception Claim&#x27;s offset is greater than the sum of the offset and thelength of the prior claim.</td></tr></table>

## LTP-013 Reception Claims Upper Bound

An LTP Reception Claim's upper bound shall be greater than or equal to the sum of the offset, length and lower bound.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 3.2.2</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 3.2.2.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that anLTP Reception Claim&#x27;s upper bound is greater than or equal to the sum ofthe offset, length and lower bound.</td></tr></table>

## LTP-014 Session Management Segments

An LTP Session Management Segment shall consist of cancel segment or cancel acknowledgement.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 3.2.4</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 3.2.4.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that anLTP Session Management Segment contains either a cancel segment orcancel acknowledgement.</td></tr></table>

## LTP-015 End of Block

The last data segment in a block shall be marked as the EOB (end of block).

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 4.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that lastdata segment in a block is marked as the EOB (end of block).</td></tr></table>

## LTP-016 Data Segment

An LTP data segment shall only contain either red-part data, green-part data, or both.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 4.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that a LTPdata segment contains either red-part, green-part, or both.</td></tr></table>

## LTP-017 End of Red-Part

The Last Data Segment for a Red-part data shall be marked as the EORP (end of red-part) segment.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 4.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that lastdata segment for a red-part data is marked as the EORP (end of red-part)segment.</td></tr></table>

## LTP-018 Maximum Transmission Unit

Data shall be subdivided into data segments within a user specified maximum transmission unit size.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 4.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 4.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that datasegments are within the specified maximum transmission unit size.</td></tr></table>

## LTP-019 Requirements from the Operating Environment

LTP shall be run directly over a data-link layer protocol.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 5</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>LTP is meant to provide additional reliability on top of an existing data linklayer.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows the LTP implementation utilizes a lower-level data-link layerprotocol.</td></tr></table>

## LTP-020 LTP Link Status

The LTP Engine shall detect the status of an LTP destination.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 5</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 5. LTP Engine needs to detectif the link was brought up or turn down.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that theLTP Engine detects if the link to the destination is active.</td></tr></table>

## LTP-021 One-way Light Time

The LTP Engine shall read the current distance from the configuration file.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 5</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 5. This is used to calculatetimeout intervals.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that theone-way light time parameter is read correctly from the configuration file.</td></tr></table>

## LTP-022 Local Data-link Layer Protocols

The content of each local data-link layer protocol frame shall contain an integer number of LTP segments.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 5</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 5. Fractions of LTP segmentswould lack the needed context and could become invalid if received out oforder.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that thecontent of each local data-link layer protocol frame is an integral numberof LTP segments.</td></tr></table>

## LTP-023 Invalid Segments

The LTP Engine shall discard invalid segments.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6. LTP segments that do notconform to the specification are discarded.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that theLTP Engine discards invalid segments.</td></tr></table>

## LTP-024 UNREACH Reason Code

The LTP Engine shall send a CR with reason-code UNREACH if the invalid data segment contains red-part data.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that theLTP Engine sends a CR with reason-code UNREACH when an invaliddata segment contains red-part data.</td></tr></table>

## LTP-025 Retransmit Checkpoint

The expiration of a countdown timer associated with a CP segment shall invoke the Cancel Session procedure for the session associated with this segment.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.7</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.7. As countdowns expire, theymust end the corresponding session via the cancel session procedure andretransmission.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows thatexpiration of a countdown timer associated with a CP segment triggersthe Cancel Session procedure.</td></tr></table>

## LTP-026 Retransmit RS

When the number of times any affected RS segment has been queued for transmission exceeds the report retransmission limit established for the local LTP engine, then the "Cancel Session" procedure shall be invoked.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.8</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.8. Need to free up resourcesif retransmission limit is exceeded by cancelling session.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that the&quot;cancel session&quot; procedure is invoked when the retransmission attemptsof RS segment(s) exceeds the report retransmission limit.</td></tr></table>

## LTP-027 Signify Red-Part Reception

Upon the arrival of a CP segment when the EORP for this session has been received and all data in the red-part of the block being transmitted in this session have been received, the LTP engine shall send a red-part reception notice to the specified client service.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.9</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.9. The LTP engine needs tonotify the sender when all of red-part has been received.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that theLTP engine sends a red-part reception notice to the specified clientservice upon the arrival of a CP segment at the end-of-red part and alldata in the red-part of the block being transmitted in this session havebeen received.</td></tr></table>

## LTP-028 Signify Green-Part Segment Arrival

Upon the arrival of a data segment whose content is a portion of the green-part of a block, the LTP engine shall send a green-part segment arrival notice to the specified client service.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.10</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.10. The LTP engine needs tonotify the sender when any green-part arrives.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that uponthe arrival of a data segment whose content is a portion of the green-partof a block, the LTP engine sends a green-part segment arrival notice tothe specified client service.</td></tr></table>

## LTP-029 Send Reception Report

When the number of reception problems detected for this session exceeds a limit established for the local LTP engine, then the "Cancel Session" procedure shall be invoked.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.11</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.11. Resources must be freedif the reception problems limit is exceeded by the cancelling session.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that thecancel session procedure is invoked when the number of receptionproblems detected for this session exceeds the limit established for thelocal LTP engine.</td></tr></table>

## LTP-030 Signify Transmission Completion Notice

A transmission-session completion notice shall be sent to the local client service associated with the session when these conditions have been met:

1. Data in the block is known to have been transmitted.

2. The entire red-part of the block is known to have been successfully received.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.12</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.12. Need to notify senderwhen entire transmission has been received, and all data is accounted for.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that atransmission-session completion notice is sent to the local client serviceassociated with the session when these conditions have been met:1. Data in the block is known to have been transmitted.2. The entire red-part of the block is known to have been successfullyreceived.</td></tr></table>

## LTP-031 Reason Code RLEXC

When the number of transmission problems for this session exceeds a limit established for the local LTP engine, a CS with reason-code RLEXC shall be appended to the transmission queue specified in the transmission request that started this session, and a transmission-session cancellation notice is sent back to the client service that requested the transmission.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.13</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>There should only be a finite number of retransmission attempts. Seesection RFC 5326 section 7.5 for the transmission session cancellationnotice.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that thenumber of transmission problems for a session exceeds a limitestablished for the local LTP engine, a CS with reason-code RLEXC shallbe appended to the transmission queue specified in the transmissionrequest that started the session, and a transmission-session cancellationnotice is sent back to the client service that requested the transmission.</td></tr></table>

## LTP-032 Stop RS Timer

The countdown timer associated with the original RS segment (identified by the report serial number of the RA segment) shall be deleted on the reception of an RA.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.14</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.14. Resources should befreed by ending countdown timers associated with RS segments.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that countdown timer associated with the original RS segment(identified by the report serial number of the RA segment) is deleted onthe reception of an RA.</td></tr></table>

## LTP-033 CS Start Cancel Timer

Upon the arrival of a link state cue indicating the de-queuing (for transmission) of a CS segment, a countdown timer for the expected arrival time of the CAS segment shall be started.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.15</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.15. Timers are needed todiagnose connection conditions.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that upon the arrival of a link state cue indicating the de-queuing(for transmission) of a CS segment, a countdown timer for the expectedarrival time of the CAS segment is started.</td></tr></table>

## LTP-034 CR Start Cancel Timer

Upon the arrival of a link state cue indicating the de-queuing (for transmission) of a CR segment, a countdown timer for the expected arrival time of the CAR segment shall be started.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.15</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.15. Timers are needed todiagnose connection conditions.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that upon the arrival of a link state cue indicating the de-queuing(for transmission) of a CR segment, a countdown timer for the expectedarrival time of the CAR segment is started.</td></tr></table>

## LTP-035 CS Acknowledge Cancellation

When a CS segment has a transmission queue-set bound for the sender, a CAS (cancel acknowledgment to block sender) segment shall be appended to the queue of internal operations traffic bound for the sender.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.17</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.17. The LTP engine needs toacknowledge when a cancel session segment is received.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that if a CS segment has a transmission queue-set bound for thesender, a CAS (cancel acknowledgment to block sender) segment isappended to the queue of internal operations traffic bound for the sender.</td></tr></table>

## LTP-036 CR Acknowledge Cancellation

When a CR segment has a transmission queue-set bound for the sender, a CAR (cancel acknowledgment to block receiver) segment shall be appended to the queue of internal operations traffic bound for the receiver.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.17</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.17. The LTP engine needs toacknowledge when a cancel session segment is received.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that if a CR segment has a transmission queue-set bound for thesender, a CAR (cancel acknowledgment to block receiver) segment isappended to the queue of internal operations traffic bound for thereceiver.</td></tr></table>

## LTP-037 CAS Stop Cancel Timer

Upon reception of a CAS segment, the timer associated with the CS segment shall be deleted.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.18</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.18. Resources must be freedby ending countdown timers associated with CS segments.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that upon reception of a CAS segment, the timer associated withthe CS segment is deleted.</td></tr></table>

## LTP-038 CAR Stop Cancel Timer

Upon reception of a CAR segment, the timer associated with the CR segment shall be deleted.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.18</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.18. Resources must be freedby ending countdown timers associated with CR segments.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that upon reception of a CAR segment, the timer associated withthe CR segment is deleted.</td></tr></table>

## LTP-039 Cancel Session

When a session is canceled, the LTP engine shall delete all queued segments from outbound traffic queues.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.19</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.19. Resources associatedwith a cancelled session must be freed.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that the LTP engine deletes all queued segments from outboundtraffic queues when a session has been canceled.</td></tr></table>

## LTP-040 Countdown Timers

When a session is cancelled, the LTP engine shall delete all countdown timers currently associated with the session.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.19</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.19. Resources associatedwith a cancelled session must be freed.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that the LTP engine deletes all countdown timers currentlyassociated with a session that has been canceled.</td></tr></table>

## LTP-041 Cancel Session Buffer

When the local LTP engine is the sender, then the remaining data retransmission buffer space allocated to a canceled session shall be released.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.19</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.19. Resources associatedwith a cancelled session must be freed.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that if the local LTP engine is the sender, then the remaining dataretransmission buffer space allocated to a canceled session is released.</td></tr></table>

## LTP-042 Close Session

Remaining countdown timers associated with a closed session shall be deleted.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.20.</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.20. Resources associatedwith a closed session must be freed.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Inspection</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a code inspectionshows that the remaining countdown timers associated with a closedsession are deleted.</td></tr></table>

## LTP-043 Handling Miscolored Segments

When miscolored data blocks are received, the LTP engine shall discard them.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.21</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.21. Need to removemiscolored data blocks from system. This procedure is triggered by thearrival of either (a) a red-part data segment whose block offset begins atan offset higher than the block offset of any green-part data segmentpreviously received for the same session or (b) a green-part data segmentwhose block offset is lower than the block offset of any red-part datasegment previously received for the same session. The arrival of asegment matching either of the above checks is a violation of the protocolrequirement of having all red-part data as the block prefix and all green-part data as the block suffix.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows thatmiscolored data blocks are discarded.</td></tr></table>

## LTP-044 Cancel Session for Miscolored Data

When miscolored data blocks are received, the local LTP engine shall cancel the session.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 6.21</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 6.21. The LTP engine shouldprevent further miscolored blocks from entering system.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that theLTP session is canceled when miscolored data has been received.</td></tr></table>

## LTP-045 UDP Port Number for LTP

The UDP port number shall be user configurable.

<table><tr><td rowspan=1 colspan=1>Status:</td><td rowspan=1 colspan=1>Vetted</td></tr><tr><td rowspan=1 colspan=1>Source:</td><td rowspan=1 colspan=1>RFC 5326 Section 10.1</td></tr><tr><td rowspan=1 colspan=1>Rationale:</td><td rowspan=1 colspan=1>Need to implement per RFC 5326 section 10.1.</td></tr><tr><td rowspan=1 colspan=1>Verification Method:</td><td rowspan=1 colspan=1>Test</td></tr><tr><td rowspan=1 colspan=1>Verification Approach:</td><td rowspan=1 colspan=1>This requirement will be considered verified when a test shows that theLTP port is configured based on the configuration file.</td></tr></table>

## APPENDIX A.—ABBREVIATIONS

<table><tr><td colspan="1" rowspan="1">Abbreviation</td><td colspan="1" rowspan="1">Definition</td></tr><tr><td colspan="1" rowspan="1">BP v</td><td colspan="1" rowspan="1">Bundle Protocol Version</td></tr><tr><td colspan="1" rowspan="1">BP</td><td colspan="1" rowspan="1">Bundle Protocol</td></tr><tr><td colspan="1" rowspan="1">URI</td><td colspan="1" rowspan="1">Uniform Resource Identifier</td></tr><tr><td colspan="1" rowspan="1">ipn</td><td colspan="1" rowspan="1">Interplanetary Network</td></tr><tr><td colspan="1" rowspan="1">ASCII</td><td colspan="1" rowspan="1">American Standard Code for Information Interchange</td></tr><tr><td colspan="1" rowspan="1">CCSDS</td><td colspan="1" rowspan="1">Consultative Committee for Space Data Systems</td></tr><tr><td colspan="1" rowspan="1">RFC</td><td colspan="1" rowspan="1">Request for Comments</td></tr><tr><td colspan="1" rowspan="1">BPGen</td><td colspan="1" rowspan="1">Bundle Protocol Generator</td></tr><tr><td colspan="1" rowspan="1">BPSendFile</td><td colspan="1" rowspan="1">Bundle Protocol Send File</td></tr><tr><td colspan="1" rowspan="1">HDTN</td><td colspan="1" rowspan="1">High-rate DTN</td></tr><tr><td colspan="1" rowspan="1">CBHE</td><td colspan="1" rowspan="1">Compressed Bundle Header Encoding</td></tr><tr><td colspan="1" rowspan="1">ID</td><td colspan="1" rowspan="1">Identification</td></tr><tr><td colspan="1" rowspan="1">DTN</td><td colspan="1" rowspan="1">Delay Tolerant Networking</td></tr><tr><td colspan="1" rowspan="1">LTP</td><td colspan="1" rowspan="1">Licklider Transmission Protocol</td></tr><tr><td colspan="1" rowspan="1">CL</td><td colspan="1" rowspan="1">Convergence Layer</td></tr><tr><td colspan="1" rowspan="1">SANA</td><td colspan="1" rowspan="1">Space Assigned Numbers Authority</td></tr><tr><td colspan="1" rowspan="1">UDP</td><td colspan="1" rowspan="1">User Datagram Protocol</td></tr><tr><td colspan="1" rowspan="1">SDNV</td><td colspan="1" rowspan="1">Self-Delimiting Numeric Value</td></tr><tr><td colspan="1" rowspan="1">MSB</td><td colspan="1" rowspan="1">Most significant bit</td></tr><tr><td colspan="1" rowspan="1">MIB</td><td colspan="1" rowspan="1">Management Information Base</td></tr><tr><td colspan="1" rowspan="1">EID</td><td colspan="1" rowspan="1">Endpoint Identifier</td></tr><tr><td colspan="1" rowspan="1">CBOR</td><td colspan="1" rowspan="1">Concise Binary Object Representation</td></tr><tr><td colspan="1" rowspan="1">CRC</td><td colspan="1" rowspan="1">Cyclic redundancy check</td></tr><tr><td colspan="1" rowspan="1">ADU</td><td colspan="1" rowspan="1">Application Data Unit</td></tr><tr><td colspan="1" rowspan="1">SSP</td><td colspan="1" rowspan="1">Scheme Specific Par</td></tr><tr><td colspan="1" rowspan="1">IANA</td><td colspan="1" rowspan="1">Internet Assigned Numbers Authority</td></tr><tr><td colspan="1" rowspan="1">BPSec</td><td colspan="1" rowspan="1">Bundle Protocol Security</td></tr><tr><td colspan="1" rowspan="1">BPAs</td><td colspan="1" rowspan="1">Bundle Protocol Agents</td></tr><tr><td colspan="1" rowspan="1">Sops</td><td colspan="1" rowspan="1">Security Operations</td></tr><tr><td colspan="1" rowspan="1">BCB</td><td colspan="1" rowspan="1">Block Confidentiality Block</td></tr><tr><td colspan="1" rowspan="1">BIB</td><td colspan="1" rowspan="1">Block Integrity Block</td></tr><tr><td colspan="1" rowspan="1">ASB</td><td colspan="1" rowspan="1">Abstract Security Block</td></tr><tr><td colspan="1" rowspan="1">AEAD</td><td colspan="1" rowspan="1">Authenticated Encryption with Associated Data</td></tr><tr><td colspan="1" rowspan="1">SABR</td><td colspan="1" rowspan="1">Schedule Aware Bundle Routing</td></tr><tr><td colspan="1" rowspan="1">CGR</td><td colspan="1" rowspan="1">Contact Graph Routing</td></tr><tr><td colspan="1" rowspan="1">CMR</td><td colspan="1" rowspan="1">Contact Multigraph Routing</td></tr><tr><td colspan="1" rowspan="1">TCPCL</td><td colspan="1" rowspan="1">Transmission Control Protocol convergence layer</td></tr><tr><td colspan="1" rowspan="1">TCP</td><td colspan="1" rowspan="1">Transmission Control Protocol</td></tr><tr><td colspan="1" rowspan="1">FIN</td><td colspan="1" rowspan="1">Finish</td></tr><tr><td colspan="1" rowspan="1">CAN TLS</td><td colspan="1" rowspan="1">Contact header flag to enable Transport Layer Security</td></tr><tr><td colspan="1" rowspan="1">TLS</td><td colspan="1" rowspan="1">Transport layer security</td></tr><tr><td colspan="1" rowspan="1">UTF</td><td colspan="1" rowspan="1">Unicode Transformation Format</td></tr><tr><td colspan="1" rowspan="1">SSL</td><td colspan="1" rowspan="1">Secure Sockets Layer</td></tr><tr><td colspan="1" rowspan="1">CA</td><td colspan="1" rowspan="1">Certificate Authority</td></tr><tr><td colspan="1" rowspan="1">SESS_INIT</td><td colspan="1" rowspan="1">Session Initialization message</td></tr><tr><td colspan="1" rowspan="1">MRU</td><td colspan="1" rowspan="1">Maximum Receive Unit</td></tr><tr><td colspan="1" rowspan="1">SESS TERM</td><td colspan="1" rowspan="1">Session Termination message</td></tr><tr><td colspan="1" rowspan="1">MSG REJECT</td><td colspan="1" rowspan="1">Message reject</td></tr><tr><td colspan="1" rowspan="1">XFER ACK</td><td colspan="1" rowspan="1">Transfer acknowledge</td></tr><tr><td colspan="1" rowspan="1">XFER_SEGMENT</td><td colspan="1" rowspan="1">Transfer segment</td></tr><tr><td colspan="1" rowspan="1">XFER_REFUSE</td><td colspan="1" rowspan="1">Transfer refuse</td></tr><tr><td colspan="1" rowspan="1">TLV</td><td colspan="1" rowspan="1">Type Length Value</td></tr><tr><td colspan="1" rowspan="1">STCP</td><td colspan="1" rowspan="1">Simple Transmission Control Protocol</td></tr><tr><td colspan="1" rowspan="1">ION</td><td colspan="1" rowspan="1">Interplanetary Overlay Network</td></tr><tr><td colspan="1" rowspan="1">STCPCL</td><td colspan="1" rowspan="1">STCP Convergence Layer</td></tr><tr><td colspan="1" rowspan="1">UDPCL</td><td colspan="1" rowspan="1">User Datagram Protocol convergence layer</td></tr><tr><td colspan="1" rowspan="1">MTU</td><td colspan="1" rowspan="1">Maximum transmission unit</td></tr><tr><td colspan="1" rowspan="1">RS</td><td colspan="1" rowspan="1">Report Segment</td></tr><tr><td colspan="1" rowspan="1">EOB</td><td colspan="1" rowspan="1">End of block</td></tr><tr><td colspan="1" rowspan="1">EORP</td><td colspan="1" rowspan="1">End of red-part</td></tr><tr><td colspan="1" rowspan="1">CR</td><td colspan="1" rowspan="1">Cancel segment from block receiver</td></tr><tr><td colspan="1" rowspan="1">CP</td><td colspan="1" rowspan="1">Checkpoint</td></tr><tr><td colspan="1" rowspan="1">RLEXC</td><td colspan="1" rowspan="1">Retransmission Limit Exceeded</td></tr><tr><td colspan="1" rowspan="1">CS</td><td colspan="1" rowspan="1">Cancel segment</td></tr><tr><td colspan="1" rowspan="1">RA</td><td colspan="1" rowspan="1">Report-acknowledgment</td></tr><tr><td colspan="1" rowspan="1">CAS</td><td colspan="1" rowspan="1">Cancel-acknowledgment segment</td></tr><tr><td colspan="1" rowspan="1">CAR</td><td colspan="1" rowspan="1">Cancel acknowledgement to block receiver</td></tr></table>

## APPENDIX B.—REVISION HISTORY

<table><tr><td rowspan=1 colspan=1>Revision</td><td rowspan=1 colspan=1>Effective Date</td><td rowspan=1 colspan=1>Description</td><td rowspan=1 colspan=1>Author</td></tr><tr><td rowspan=1 colspan=1>Draft</td><td rowspan=1 colspan=1>03/22/2024</td><td rowspan=1 colspan=1>Initial Requirement Analysis</td><td rowspan=1 colspan=1>Rachel Dudukovich</td></tr></table>