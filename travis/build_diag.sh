#!/bin/bash

# Build the Diagrams
set -x

# Move to diagram directory, fail build if failure
cd plantuml || exit 1

diagrams=$(find . -type f -regex ".*\.pu$")

all_good=1

for diagram in ${diagrams} ; do

  # Build this Diagram
  java -jar ../travis/artifacts/plantuml.jar -tsvg "${diagram}"

  wasgood=$?

  if [[ ${wasgood} -gt 0 ]] ; then
    # Diagram didn't work
    echo -e "Issue with Diagram ${diagram}. Plese investigate."
    all_good=0
  fi
done

if [[ ${all_good} -eq 0 ]] ; then
  echo -e "Issues with Diagrams. Breaking Build"
  exit 1
else
  echo -e "Diagrams Completed."
fi

mkdir /home/travis/plantuml/

cp ./*.svg /home/travis/plantuml

exit 0


