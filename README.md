# YaBCMOrganizer
This tool is here to help out with creating and modifying BCMs. In addition to giving a more organized look into what the various entries do, it can also

* Copy, Delete, and Paste entries
* Copy an entry and its children in full and add them all elsewhere while preserving its hierarchy
* Clipboard can be shared between multiple instances to allow easy copying/pasting between different BCM's
* Automatically reindexes for the OCD
* Easy link to the BCM section of the Skill/Moveset guide for more explanation on the various thing

# Credits
* DemonBoy - Idea and testing
* Eternity - Genser source code helped with the nitty gritty technical bits of the BCM file structure.
* Smithers & LazyBones - For the Skill/Moveset guide and the research into what each BCM entry field does.


# Changelog
```
0.1.0 - Initial release
0.1.1 - Fixed order of BAC Charge and BAC Airborne
0.1.2 - Add search/replace function
0.1.3 - Fixed floating point entries not being able to go negative
0.1.4 - Fixed issue when searching sometimes freezing the program
0.1.5 - Fixed issue saving
0.1.6 - Removed conflicting options and shortcuts from main edit menu
0.1.7 - Added ability to drag/associate files to exe to open them
0.1.8 - Fixed floats not updating sometimes
0.2.0 - Added child/sibling links to misc panel, changed backend treectrl for displaying tree,
        allow limited multi select for deleting multiple entries, removed prompt asking to keep children when deleting.
0.2.1 - Fixed bug where entry0 wasn't added when saving.  Improved performance on copying large entries.
0.2.2 - Add automatic backup creation on saving
0.2.3 - Improved editing performance with very large BCM's, fixed child/sibling indexes cutting off at 32767
0.2.4 - Added primary activator conditions
0.2.5 - Fixed find/replace dialogs so it works with int/hex/float
0.2.6 - Added new flag selections in unknown and BAC tabs
        fixed names on Primary Activator Conditions 
```
