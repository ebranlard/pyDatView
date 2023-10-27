
# Creating a new release

Steps:
- Change version in setup.py
- Change PROG\_VERSION in pydateview/main.py
- Change version in installler.cfg
- Change CURRENT\_DEV\_TAG in .github/workflows/tests.yml   (not pretty...)
- Commit changes and push to pull request
- Merge pull request from old to new version

- Tag new version v0.x:
     git tag -a v0.x
- Push tags:
     git push --tags
- Github actions looks at GITHUB_REF to see if it's a tag. If it's a tag, it should push to it.
  Otherwise, it pushes to the tag defined by CURRENT_DEV_TAG

- Make sure things worked

- checkout dev and create a new dev tag, e.g. v0.3-dev


- Rename vdev to v0.3-dev
  git tag v0.3-dev vdev
  git tag -d vdev
  git push origin v0.3-dev :vdev





#Misc notes:


## Delete a tag locally and remote
git tag -d vtag
git push --delete origin vtag

## Rename a tag locally and remote
git tag new old
git tag -d old
git push origin new :old




# Profiling
Dependencies:
```
pip install snakeviz pyprof2calltree
#or
pip install viztracer
```

Profile:
```
make prof
```

Runs the following:
```
viztracer  .\tests\prof_all.py
vizviewer.exe .\result.json
```

