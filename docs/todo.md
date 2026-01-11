# TODO

## testing

- [x] --version command
- [x] migrate uv package manager instead of venv-wrapper #p2 #urgent
- [x] #28 Fix spinner.
- [x] last-backup-info.json move it to .config as a metadata.json or info.json

## in-progress

- [ ] cleanup codes; remove unused methods, variables, imports, etc.
- [ ] keep more than one backup info in config file? one for current, one for previous probably better.
- [ ] update last backup date to config file or somewhere else
      "last_backup": null
- [ ] use modern encryption command?

## todo

- [ ] path uses `//` two of them (it is warning and not error but still maybe better to fix it)
      File already exist: /home/developer/Documents/backup-for-cloud//13-04-2025.tar.xz
- [ ] multiple machine setup support with our config file?
- [ ] #12 Dotfiles Compability like .zshenv .zshrc but those are not directory, so we need to make another way to backup those

## done

- [x] Switch zstd from xz
- [x] keepachangelog template for changelog file
- [x] add success after backup and encryption
- [x] folder/module structure
- [x] ask 2 time for password
- [x] backup choice not work
- [x] #23 feat: Refactor code structure
- [x] write all of config files with `~` instead of full path
- [x] move .log files to .config
- [x] #13 Create requirements.txt
- [x] unittest
- [x] is command design pattern is correct?
- [x] #27 update dependencies
- [x] add fpath with $HOME #p1 #urgent

```bash
fpath=($HOME/.config/zsh/completions $fpath)
```
