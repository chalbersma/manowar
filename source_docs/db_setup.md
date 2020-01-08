# DB Setup

## Yoyo

Setting up the database has been reworked to utilize
[yoyo](https://marcosschroh.github.io/yoyo-database-migrations/). You need a
modern mariadb Database (10.x and higher) available to you named `manowar2` and
and administraive user.

Then in the `yoyo_steps` directory you need to create a `yoyo.ini` file (see the
`yoyo.ini.sample` as an example). In it you need to edit the target database with
your administrator username and password. Additionally you'll need to populate
credentials for your big 3 users, the api user, the storage user and the analyze
user.

I'd encourage managing this file with a change management system so that you can
better manage these secrets contained here.

## Application

Inside the `yoyo_steps` directory do the following:

```
yoyo showmigrations
```

This should show you the migrations that are available and haven't been applied yet.
If you're downgrading, you'll want to utilize the rollback options. But generally a
simple `apply` should get you the latest database version for your version of manowar.


