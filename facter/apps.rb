# Create application_ facts based on application_usage database.
#
# Copyright 2011 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


begin
  require 'sqlite3'

  appdb = "/var/db/application_usage.sqlite"
  query = 'select bundle_id, last_time from application_usage ' +
           'where event="launch"'

  if File.exist?(appdb) then
    begin
      db = SQLite3::Database.new(appdb)
      db.results_as_hash = true
      row = db.execute(query)

      row.each_with_index do |appinfo, i|
        appname = appinfo["bundle_id"]
        appname = "UNKNOWN#{i}" if appname.nil?
        factname = "app_lastrun_" + appname
        appdate = appinfo["last_time"]
        appdate = "UNKNOWN" if appdate.nil?
        Facter.add(factname) do
          setcode do
            appdate
          end
        end
      end

    rescue SQLite3::SQLException
      warn('Error parsing application usage database')
    end
  else
    warn('No application usage database found')
  end
rescue LoadError
  warn('No sqlite3 support')
end
