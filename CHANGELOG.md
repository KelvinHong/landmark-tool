# Change Log
All notable changes to the project "LandmarkTool" will be documented in this file.
 
The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).
 
## [Unreleased] - yyyy-mm-dd

- User may jump through images. 
- User may export image during annotation.
- Convert the project into a Docker Image. 
- User may customize landmark style, such as cross, plus sign, transparent, etc.
 
 
## [0.1.0] - 2022-04-05
  
First Official Version of LandmarkTool.
 
### Added
- Users are able to import image dataset and do labeling on it.
- Support saving, user just need to save before exit, then can 
    resume back to the work.
- Support basic functions such as point annotation, last point removal, 
    redo whole image. 
- Support point shifting, which will move point during annotation, 
    not necessary need to be the last point. 
- Support both Fixed Number Landmark Annotation and Dynamic Number 
    Landmark Annotation.