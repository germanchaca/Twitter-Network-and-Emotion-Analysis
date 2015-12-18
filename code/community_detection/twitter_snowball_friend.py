import tweepy
import sys
import time
import os
import json
import csv
import traceback

FOLLOWING_DIR = os.path.abspath('following')
TWITTER_USERS_DIR = os.path.abspath('twitter-users')
MAX_FRIENDS = 500
MAX_FOLLOWERS = 200
FRIENDS_OF_FRIENDS_LIMIT = 250
FOLLOWERS_OF_FOLLOWERS_LIMIT = 200
 
if not os.path.exists(FOLLOWING_DIR):
    os.makedirs(FOLLOWING_DIR)
if not os.path.exists(TWITTER_USERS_DIR):
    os.makedirs(TWITTER_USERS_DIR)

CONSUMER_KEY = 'XRH8Wd2ZaDhAUmA5kEY5qGTrp'
CONSUMER_SECRET = '0rWg61r9DOMGFLXq5ebgLnDRC8xHqV1dgZYyaPVdwGO0sa6f4v'
ACCESS_TOKEN = '3154159514-wPdXqU9ayRiFEkzjfHVmFqVuDzQdK5SYJbsymH6'
ACCESS_TOKEN_SECRET = 'KzRfzz9AHDkjB2r15dPsXcaqxzzkSGF5qDeTtnRveOEDn'

auth = tweepy.OAuthHandler(CONSUMER_KEY,CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN,ACCESS_TOKEN_SECRET)

api = tweepy.API(auth)

# Encode string into ascii
enc = lambda x: x.encode('ascii', errors='ignore')

def snowball_sampling(g, center, max_depth = 1, current_depth = 0, taboo_list = []):
    print center, current_depth, max_depth, taboo_list
    
    if current_depth == max_depth:
        print 'out of depth'
        return taboo_list
    if center in taboo_list:
        # Visited this person -- exit
        return taboo_list
    else:
        # New person!  Don't visit again
        taboo_list.append(center)
    
    # lj.read_lj_friends(g, center)
    
    for node in g.neighbors(center):
        # Iterate through all friends of the central node, and
        # recursively call snowball sampling
        taboo_list = snowball_sampling(g, node, current_depth = current_depth + 1, 
                                       max_depth = max_depth, taboo_list = taboo_list)
    
    return taboo_list

def get_follower_ids(centre, max_depth=1, current_depth=0, taboo_list=[]):
 
    # print 'current depth: %d, max depth: %d' % (current_depth, max_depth)
    # print 'taboo list: ', ','.join([ str(i) for i in taboo_list ])

    if current_depth == max_depth:
        print 'out of depth'
        return taboo_list
 
    if centre in taboo_list:
        # we've been here before
        print 'Already been here.'
        return taboo_list
    else:
        taboo_list.append(centre)
 
    try:
        userfname = os.path.join('twitter-users', str(centre) + '.json')
        if not os.path.exists(userfname):
            print 'Retrieving user details for twitter id %s' % str(centre)
            while True:
                try:
                    user = api.get_user(centre)
 
                    d = {'name': user.name,
                         'screen_name': user.screen_name,
                         'id': user.id,
                         'friends_count': user.friends_count,
                         'followers_count': user.followers_count,
                         'followers_ids': user.followers_ids(),
                         'friends_ids' : user.friends_ids()}
 
                    with open(userfname, 'w') as outf:
                        outf.write(json.dumps(d, indent=1))

                    user = d
                    break
                except tweepy.TweepError, error:
                    print type(error)
 
                    if str(error) == 'Not authorized.':
                        print 'Can''t access user data - not authorized.'
                        return taboo_list
 
                    if str(error) == 'User has been suspended.':
                        print 'User suspended.'
                        return taboo_list
 
                    errorObj = error[0][0]
 
                    print errorObj
 
                    if errorObj['message'] == 'Rate limit exceeded':
                        print 'Rate limited. Sleeping for 15 minutes.'
                        time.sleep(15 * 60 + 15)
                        continue
 
                    return taboo_list
        else:
            user = json.loads(file(userfname).read())
 
        screen_name = enc(user['screen_name'])
        fname = os.path.join(FOLLOWING_DIR, screen_name + '.csv')
        friendids = []
 
        # only retrieve friends of TED... screen names
        if not os.path.exists(fname):
            print 'No cached data for screen name "%s"' % screen_name
            with open(fname, 'w') as outf:
                params = (enc(user['name']), screen_name)
                print 'Retrieving followers for user "%s" (%s)' % params
                writer = csv.writer(outf,dialect='excel')
                
                # page over followers
                c = tweepy.Cursor(api.friends, id=user['id']).items()

                #follower_count = 0
                friend_count = 0
                #friend_set = set()
                #follower_set = set()
                
                while True:
                    try:
                        follower = c.next()
                        friendids.append(follower.id)
                        params = (follower.id, enc(follower.screen_name), enc(follower.name))
                        writer.writerow(params)
                        friend_count += 1
                        if friend_count >= MAX_FRIENDS:
                            print "Reached max no. of followers for '%s'." % follower.screen_name
                            break
                    except tweepy.TweepError, error:
                        # hit rate limit, sleep for 15 minutes
                        print 'Rate limited. Sleeping for 15 minutes.'
                        time.sleep(15 * 60 + 15)
                        continue
                    except StopIteration:
                        break
                
        else:
            with open(fname, 'r') as outf:
                reader = csv.reader(outf,dialect='excel')
                friendids = [row[0] for row in reader]
 
        print 'Found %d followers for %s' % (len(friendids), screen_name)

        # get friends of friends
        cd = current_depth
        if cd+1 < max_depth:
            for fid in friendids[:FRIENDS_OF_FRIENDS_LIMIT]:
                taboo_list = get_follower_ids(fid, max_depth=max_depth,
                    current_depth=cd+1, taboo_list=taboo_list)

        if cd+1 < max_depth and len(friendids) > FOLLOWERS_OF_FOLLOWERS_LIMIT:
            print 'Not all followers retrieved for %s.' % screen_name
 
    except Exception, error:
        print 'Error retrieving followers for user id: ', centre
        print str(error)
        traceback.print_exc()
 
        if os.path.exists(fname):
             os.remove(fname)
             print 'Removed file "%s".' % fname
 
        sys.exit(1)
 
    return taboo_list

twitter_screenname = 'avbytes'
matches = api.lookup_users(screen_names=[twitter_screenname])
depth = 2
if len(matches) == 1:
    get_follower_ids(matches[0].id, max_depth=depth)
else:
    print 'Sorry, could not find twitter user with screen name: %s' % twitter_screenname

# for frd in tweepy.Cursor(api.friends, id=user['id']).items():
#     try:
#         friend_set.add(frd)
#         friend_count += 1
#         params = (frd.id, enc(frd.screen_name), enc(frd.name))
#         if(friend_count >= MAX_FRIENDS):
#             print "Reached max number of friends for %s." % frd.screen_name
#             break

#     except tweepy.TweepError:
#         # hit rate limit, sleep for 15 minutes
#         print 'Rate limited. Sleeping for 15 minutes.'
#         time.sleep(15 * 60 + 15)
#         continue

# for flw in tweepy.Cursor(api.followers, id=user['id']).items():
#     try:
#         follower_set.add(flw)
#         follower_count += 1
#         if(follower_count >= MAX_FOLLOWERS):
#             print "Reached max number of followers for %s." % flw.screen_name
#             break

#     except tweepy.TweepError:
#         # hit rate limit, sleep for 15 minutes
#         print 'Rate limited. Sleeping for 15 minutes.'
#         time.sleep(15 * 60 + 15)
#         continue
# ids_friend = set(x.id for x in friend_set)
# intersect_set = [item for item in follower_set if item.id in ids_friend]

# for ele in intersect_set:
#     try:
#         friendids.append(ele.id)
#         params = (ele.id, enc(ele.screen_name), enc(ele.name))
#         writer.writerow(params)
#     except IOError:
#         print "Error retrieving intersection users for %s." % ele.screen_name
#         traceback.print_exc()


# for flw in tweepy.Cursor(api.followers, id=user['id']).items():
#     try:
#         friendids.append(flw.id)
#         params = (flw.id, enc(flw.screen_name), enc(flw.name))
#         #outf.write('%s\t%s\t%s\n' % params)
#         writer.writerow(params)
#         friend_count += 1
#         if friend_count >= MAX_FRIENDS:
#             print "Reached max number of friends for %s." % flw.screen_name
#             break
#     except tweepy.TweepError:
#         # hit rate limit, sleep for 15 minutes
#         print 'Rate limited. Sleeping for 15 minutes.'
#         time.sleep(15 * 60 + 15)
#         continue

# while True:
#     try:
#         friend = c.next()
#         friendids.append(friend.id)
#         params = (friend.id, enc(friend.screen_name), enc(friend.name))
#         outf.write('%s\t%s\t%s\n' % params)
#         friend_count += 1
#         if friend_count >= MAX_FRIENDS:
#             print 'Reached max no. of friends for "%s".' % friend.screen_name
#             break
#     except tweepy.TweepError:
#         # hit rate limit, sleep for 15 minutes
#         print 'Rate limited. Sleeping for 15 minutes.'
#         time.sleep(15 * 60 + 15)
#         continue
#     except StopIteration:
#         break