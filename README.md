# gts-ginnys-tonic

Random stuff I made to play around with the GotoSocial API.
I don't know what I'm doing (both in coding, or in what I'm coding. Fun!)

## Initial Setup

Initial setup should only be required one time; subsequent uses will use the cached credentials
created during setup.

### Creating a GTS OAuth Application

- Create a new application in the GoToSocial Settings UI (eg, https://yourinstance.social/settings)
- In the root folder with `./tool.py`, create a file called `application.json` with the client ID and client secret you get from your GTS settings dashboard. It should look like this, but you put ur stuff in the quotes!

```json
{
    "client_id": "",
    "client_secret": ""
}
```

- Edit `./tool.py` and change the `INSTANCE_BASE_URL` variable to the base URL for your GTS instance.
You shouldn't need to edit any of the other variables probably.
- Run `./tool.py` to fetch your account's specific credentials.

  - Generally speaking you should be able to run the tool with a stock Python 3 installation. It's probably one of the following two commands (you only need to run whichever one works)

```shell
# If your system only has `python3` as a binary (MacOS)
python3 ./tool.py command
# If your system only has `python` as a binary (many linuxes)
python ./tool.py command
# Both binaries might work, in which case just choose your favorite.
```

- On first run, it will open a browser and open a login page. The login page is hosted by your own instance -
the tool **never sees or directly requests your credentials**. This process gives the tool a token which allows it
to act as you (so that it can do the various functions below). You are always free to revoke that token and/or remove
the local file in which the token is cached. At which point the tool no longer has *any* access to your account.
    - These are then cached into a local file, `credentials.json` which you should keep secure and secret.

- The tool should now be fully ready to run!

## Current Commands

### unfollow

#### Usage

`unfollow [gotosocial_user_id]`

Unfollows a single user identified by the provided user ID in GotoSocial (this will be a [ULID](https://github.com/ulid/spec) and look something like `01ARZ3NDEKTSV4RRFFQ69G5FAV`)

#### Important Usage Notes

You cannot specify what most people think of as a user ID (eg, `gintoxicating@transister.social` or `@gintoxicating@transister.social`), you must specify the local GTS user id (looks like `01ARZ3NDEKTSV4RRFFQ69G5FAV`)

#### Why did you add this?

I imported my following list blindly, and ended up following a lot of inactive/dormant accounts. I wanted to remove those, and doing so was a bit cumbersome through the UI I use.

### moots

#### Usage

`moots`

Loads your followers and following, and shows the difference between those sets of users. For each user it
lists out details like their follower/following count, the last post **your instance has seen from that user**,
and a few other tidbits.

#### Important Usage Notes

The last post timestamp will only reflect posts **your instance has seen**. Typically this means only new posts from after your follow (I'm guessing unless someone else on your instance already followed that user).

This command is pretty hacked together specific to my current use case. I want to clean it up to provide a bit more
customizability in the search.

#### Why did you add this?

As I mentioned above, I blindly imported a list of people to follow from my old account. I wanted to do some
cleanup and identify:

* Users who are inactive.
* Users who appear to be follow-spamming (eg, they have thousands of "following" with only tens of "followers")
* Quickly look over the names and account details of folks (there are some types of accounts which I just don't vibe with and which are pretty easy to pick out through patterns in some of the returned information)

The outputted data includes the local user ID, which allows me to run the `unfollow` command.

## TODO

### add command: `onthisday`

Show a list of historical posts from this day in history (eg, if it's 2025-12-22, show posts from 2024-12-22, 2023-12-22, etc)

### add command: `search`

Search *your posts* (and only your posts), and provide in-stream links to the GTS UI.
(Ie, link to the profile page around this post and not just the individual post)

### add command: `movepost`

Move a post with a given ID to another GTS account. This would require me storing multiple credentials.

### add command: `accounts` (or credentials?)

Support commands to get, remove, and choose different accounts and their OAuth credentials for
use with the tool. Right now a single login is supported.

Idetally each credential could also request a limited scope if desired. If not writing (eg, you don't
want to use `unfollow`) it would be safer to allow a user to only request a `read` scoped token.

### add command: `createapplication`

Basically automatically register the application instead of the manual steps above to create `application.json`

### add command: `gotodate` (name sucks)

Open up a user's profile page to the page which has posts starting at/around a given date. Since GTS uses
UILDs this should be pretty straightforward I think.

### add command: `createembed` (name sucks)

A hacky way to get a snippet of embedable HTML or something which renders a user's own post on an external
site. This would only be possible for a user's own posts, because after it's exported it would no longer respect
delete/update commands.

This wouldn't show any of the various counters since those would possibly get out of date.

It would also link to the single post page on the instance itself.

### add command: `bangers`

Search and display your "best" posts.

I know I shouldn't care about internet posts don't at me.

### add command: `goodgirl`

Call the user a good girl.

### add command: `metrics`

User's post metrics. A heatmap of when they post, maybe some charts and stuff. Akin to what you
can get on Sharkey. This isn't checking internet points: it wouldn't chart/graph received likes, etc. Just
gives a user an idea of their activity levels posting.

### cleanup: more secure credentials storage

This gets complicated especially cross-platform, and I personally have always resorted to storing the
credentials in plain text even with properly-designed and implemented tools like [slurp](https://github.com/VyrCossont/slurp) so I might not be smart enough to ever do this.

### cleanup: full configuration without editing the python

Especially the base URL my girl.

### cleanup: way better logging and data export

Logs need to be way less all over the place. Additionally commands like `moots` could export JSON of
the various lists of data they loaded. Not necessarily used as a cache, but would allow a more structured
way to look at followers/following/etc.

### probably won't happen: ginnys tonic as a service

For some of these commands, allowing other users to login to their instance without self-configuration
would be kinda neat. Especially for fun little things like showing on-this-day posts.

This could also open up some ability to let users embed some of this stuff on their own web 1.0 homepages (maybe?)