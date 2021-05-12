# Training Artifacts

Each folder contains a different training module and related artifacts and exercises for a given topic.  
The numbering implies teaching sequence but each folder is stand-alone and can be used without running through the exercises in an "earlier" module.

## To Use These Artifacts

- Make a directory in which you will run the exercises and cd to that folder.
  - e.g. `mkdir training && cd training`
- In github navigate to the folder containing a training modle (e.g. 1_stack-basics) in git and copy the URL.
- In you `training` folder (or whatever you called it above), create a folder for the module you are going to do and cd to that folder.
  - e.g. `mkdir stack_basics && cd stack_basics`
- Run pulumi new using the URL copied above.
  - e.g. `pulumi new https://github.com/..../1_stack_basics`
  - This will pull down the material and set up your environment.
- Open the main program file (e.g. **main**.py) and go through the exercises described in the prolog section of the file.
  - Solutions for the exercises are provided in the `solutions` folder.
