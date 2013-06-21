import requests, json
import base64
import os
from binstar_client.utils import compute_hash
from binstar_client.requests_ext import stream_multipart
import sys
# from poster.encode import multipart_encode
# from poster.streaminghttp import register_openers
# import urllib2
# register_openers()

class BinstarError(Exception):
    pass

class Unauthorized(BinstarError):
    pass

class NotFound(IndexError, BinstarError):
    pass

def jencode(payload):
    return base64.b64encode(json.dumps(payload))
    
class Binstar():
    '''
    An object that represents interfaces with the binstar.org restful API.
    
    :param token: a token generated by Binstar.authenticate or None for 
                  an anonymous user. 
    '''
    
    def __init__(self, token=None, domain='https://api.binstar.org'):
        self.session = requests.Session()
        self.token = token
        if token:
            self.session.headers.update({'Authorization': 'token %s' % (token)})
        
        self.domain = domain
    
    def authenticate(self, username, password, application, application_url=None, scopes=['package'],):
        '''
        Use basic authentication to create an authentication token using the interface below. 
        With this technique, a username and password need not be stored permanently, and the user can 
        revoke access at any time.
        
        :param username: The users name
        :param password: The users password
        :param application: The application that is requesting access
        :param application_url: The application's home page 
        :param scopes: Scopes let you specify exactly what type of access you need. Scopes limit access for the tokens.
        '''
        
        url = '%s/authentications' % (self.domain)
        payload = {"scopes": scopes, "note": application, "note_url": application_url}
        data = base64.b64encode(json.dumps(payload))
        res = self.session.post(url, auth=(username, password), data=data, verify=True)
        self._check_response(res)
        res = res.json()
        token = res['token']
        self.session.headers.update({'Authorization': 'token %s' % (token)})
        return token
        
    def remove_authentication(self, token):
        url = '%s/authentications' % (self.domain)
        res = self.session.delete(url, verify=True)
        self._check_response(res)
        
    def _check_response(self, res, allowed=[200]):
        if not res.status_code in allowed:
            try:
                data = res.json()
            except:
                msg = 'Undefined error'
            else: 
                msg = data.get('error', 'Undefined error')
            ErrCls = BinstarError
            if res.status_code == 401:
                ErrCls = Unauthorized
            elif res.status_code == 404:
                ErrCls = NotFound
            raise ErrCls(msg, res.status_code)
        
    def user(self, login=None):
        '''
        Get user infomration.
        
        :param login: (optional) the login name of the user or None. If login is None
                      this method will return the information of the authenticated user.
        '''
        if login:
            url = '%s/user/%s' % (self.domain, login)
        else:
            url = '%s/user' % (self.domain)
        
        res = self.session.get(url, verify=True)
        self._check_response(res)
        
        return res.json()
    
    def user_packages(self, login=None):
        '''
        Returns a list of packages for a given user
        
        :param login: (optional) the login name of the user or None. If login is None
                      this method will return the packages for the authenticated user.

        '''
        if login:
            url = '%s/packages/%s' % (self.domain, login)
        else:
            url = '%s/packages' % (self.domain)
        
        res = self.session.get(url, verify=True)
        self._check_response(res)
        
        return res.json()
    
    def package(self, login, package_name):
        '''
        Get infomration about a specific package
        
        :param login: the login of the package owner 
        :param package_name: the name of the package
        '''
        url = '%s/package/%s/%s' % (self.domain, login, package_name)
        res = self.session.get(url, verify=True)
        self._check_response(res)
        
        return res.json()
    
    def all_packages(self, modified_after=None):
        '''
        '''
        url = '%s/package_listing' % (self.domain)
        data = {'modified_after':modified_after or ''}
        res = self.session.get(url, data=data, verify=True)
        self._check_response(res)
        return res.json()

    
    def add_package(self, login, package_name,
                    package_type,
                    summary=None,
                    license=None,
                    license_url=None,
                    public=True,
                    attrs=None,
                    host_publicly=None):
        '''
        Add a new package to a users account 
        
        :param login: the login of the package owner 
        :param package_name: the name of the package to be created
        :param package_type: A type identifyer for the package (eg. 'pypi' or 'conda', etc.)
        :param summary: A short summary about the package
        :param license: the name of the package license
        :param license_url: the url of the package license
        :param public: if true then the package will be hosted publicly
        :param attrs: A dictionary of extra attributes for this package 
        :param host_publicly: TODO: describe
        '''
        url = '%s/package/%s/%s' % (self.domain, login, package_name)
        
        attrs = attrs or {}
        attrs['summary'] = summary
        attrs['license'] = {'name':license, 'url':license_url}
        
        payload = dict(package_type=package_type,
                       public=public,
                       public_attrs=attrs or {},
                       host_publicly=host_publicly)
        
        data = jencode(payload)
        res = self.session.post(url, verify=True, data=data)
        self._check_response(res)
        return res.json()
    
    def release(self, login, package_name, version):
        '''
        Get information about a specific release
        
        :param login: the login of the package owner 
        :param package_name: the name of the package
        :param version: the name of the package
        '''
        url = '%s/release/%s/%s/%s' % (self.domain, login, package_name, version)
        res = self.session.get(url, verify=True)
        self._check_response(res)
        return res.json()
    
    def add_release(self, login, package_name, version, requirements, announce, description):
        '''
        Add a new release to a package.
        
        :param login: the login of the package owner 
        :param package_name: the name of the package 
        :param version: the version string of the release
        :param requirements: A dict of requirements TODO: describe 
        :param announce: An announcement that will be posted to all package watchers
        :param description: A long description about the package
        '''
        
        url = '%s/release/%s/%s/%s' % (self.domain, login, package_name, version)
        
        payload = {'requirements':requirements, 'announce':announce, 'description':description}
        data = jencode(payload)
        res = self.session.post(url, data=data, verify=True)
        self._check_response(res)
        return res.json()

    def remove_dist(self, login, package_name, release, basename=None, _id=None):
        
        if basename:
            url = '%s/dist/%s/%s/%s/%s' % (self.domain, login, package_name, release, basename)
        elif _id:
            url = '%s/dist/%s/%s/%s/-/%s' % (self.domain, login, package_name, release, _id)
        else:
            raise TypeError("method remove_dist expects either 'basename' or '_id' arguments")
            
        print 'url', url
        res = self.session.delete(url, verify=True)
        self._check_response(res)
        return res.json()
        
    
    def download(self, login, package_name, release, basename, md5=None):
        '''
        Dowload a package distribution
        
        :param login: the login of the package owner 
        :param package_name: the name of the package 
        :param version: the version string of the release
        :param basename: the basename of the distribution to download
        :param md5: (optional) an md5 hash of the download if given and the package has not changed
                    None will be returned
        
        :returns: a file like object or None 
        '''
        
        url = '%s/download/%s/%s/%s/%s' % (self.domain, login, package_name, release, basename)
        if md5:
            headers = {'ETag':md5, }
        else:
            headers = {}
        
        res = self.session.get(url, verify=True, headers=headers, allow_redirects=False)
        self._check_response(res, allowed=[302, 304])
        
        if res.status_code == 304:
            return None
        elif res.status_code == 302:
            res2 = requests.get(res.headers['location'], stream=True, verify=True)
            return res2.raw
            
    
    def upload(self, login, package_name, release, basename, fd, description='', md5=None, size=None, attrs=None, callback=None):
        '''
        Upload a new distribution to a package release. 
        
        :param login: the login of the package owner 
        :param package_name: the name of the package 
        :param version: the version string of the release
        :param basename: the basename of the distribution to download
        :param fd: a file like object to upload
        :param description: (optional) a short description about the file
        :param attrs: any extra attributes about the file (eg. build=1, pyversion='2.7', os='osx')

        '''
        url = '%s/stage/%s/%s/%s/%s' % (self.domain, login, package_name, release, basename)
        if attrs is None:
            attrs = {}
        if not isinstance(attrs, dict):
            raise TypeError('argument attrs must be a dictionary')
        
        payload = dict(description=description, attrs=attrs)
        data = jencode(payload)
        res = self.session.post(url, data=data, verify=True)
        self._check_response(res)
        obj = res.json()
        
        s3url = obj['s3_url']
        s3data = obj['s3form_data']
        
        if md5 is None:
            _hexmd5, b64md5, size = compute_hash(fd, size=size)
        elif size is None:
            spos = fd.tell()
            fd.seek(0, os.SEEK_END)
            size = fd.tell() - spos
            fd.seek(spos)
        
        s3data['Content-Length'] = size
        s3data['Content-MD5'] = b64md5
        
        if sys.platform.startswith('win'):
            s3res = requests.post(s3url, data=s3data, files={'file':(basename, fd)}, verify=True, timeout=10*60*60, headers=headers)
        else:        
            data_stream, headers = stream_multipart(s3data, files={'file':(basename, fd)}, 
                                           callback=callback)
             
            s3res = requests.post(s3url, data=data_stream, verify=True, timeout=10*60*60, headers=headers)
         
        if s3res.status_code != 201:
            print s3res.text 
            print 
            print 
            raise BinstarError('Error uploading to s3', s3res.status_code)
        
        url = '%s/commit/%s/%s/%s/%s' % (self.domain, login, package_name, release, basename)
        payload = dict(dist_id=obj['dist_id'])
        data = jencode(payload)
        res = self.session.post(url, data=data, verify=True)
        self._check_response(res)
        
        return res.json()
    

    def groups(self, owner=None):
        if owner:
            url = '%s/groups/%s' % (self.domain, owner)
        else:
            url = '%s/groups' % (self.domain, )
            
        res = self.session.get(url, verify=True)
        self._check_response(res)
        
        return res.json()

    def group(self, owner, group_name):
        url = '%s/group/%s/%s' % (self.domain, owner, group_name)
        res = self.session.get(url, verify=True)
        self._check_response(res)
        return res.json()

    def group_members(self, org, name):
        url = '%s/group/%s/%s/members' % (self.domain, org, name)
        res = self.session.get(url, verify=True)
        self._check_response(res)
        
        return res.json()
    
    def is_group_member(self, org, name, member):
        url = '%s/group/%s/%s/members/%s' % (self.domain, org, name,member)
        res = self.session.get(url, verify=True)
        self._check_response(res, [204, 404])
        return res.status_code == 204
    
    def add_group_member(self, org, name, member):
        url = '%s/group/%s/%s/members/%s' % (self.domain, org, name,member)
        res = self.session.put(url, verify=True)
        self._check_response(res, [204])
        return

    def remove_group_member(self, org, name, member):
        url = '%s/group/%s/%s/members/%s' % (self.domain, org, name,member)
        res = self.session.delete(url, verify=True)
        self._check_response(res, [204])
        return
    
    def remove_group_package(self, org, name, package):
        url = '%s/group/%s/%s/packages/%s' % (self.domain, org, name, package)
        res = self.session.delete(url, verify=True)
        self._check_response(res, [204])
        return
    
    def group_packages(self, org, name):
        url = '%s/group/%s/%s/packages' % (self.domain, org, name)
        res = self.session.get(url, verify=True)
        self._check_response(res, [200])
        return res.json()
    
    def add_group_package(self, org, name, package):
        url = '%s/group/%s/%s/packages/%s' % (self.domain, org, name, package)
        res = self.session.put(url, verify=True)
        self._check_response(res, [204])
        return

    def add_group(self, org, name, perms='read'):
        url = '%s/group/%s/%s' % (self.domain, org, name)

        payload = dict(perms=perms)
        data = jencode(payload)

        res = self.session.post(url, data=data, verify=True)
        self._check_response(res, [204])
        
        return