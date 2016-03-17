# Copyright 2016 Google Inc. All Rights Reserved.
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
#
# Cache custom facter facts. The code to gather fact data has a configurable
# timeout and the length of time to cache each fact can be configured also.
#
# Usage:
#
#   require_relative 'cache.rb'
#
#   Facter.add('my_custom_fact') do
#     setcode do
#       # The timeout defaults to 120 seconds.
#       get_fact_value_with_timeout('my_custom_fact', FactCache::DAY) do
#         Some complex task to calculate the fact value..
#         return val
#       end
#     end
#   end
#
#   Facter.add('my_other_fact') do
#     setcode do
#       get_fact_value_with_timeout('my_other_fact', FactCache::HOUR, 30) do
#         Some complex task that must complete within 30 seconds..
#         val
#       end
#     end
#   end
#
#   Facter.add('my_third_fact') do
#     setcode do
#       # Call a method to get the fact value
#       get_fact_value('my_third_fact', FactCache::WEEK, 'my_method', 'method_arg1')
#     end
#   end
#
#   Cache path defaults to /var/db/puppet/cached_facts.yaml. If the directory
#   does not exist it will be created when necessary but you should use Puppet
#   to ensure the permissions are correct.
#
#   Caching can be disabled with the environment variable FACTER_NOCACHE:
#   FACTER_NOCACHE=1 facter -p
#
#   The cache path can be switched using the environment variable
#   FACTER_CACHEPATH:
#   FACTER_CACHEPATH=/tmp/mycache.yaml facter -p
#

require 'fileutils'
require 'singleton'
require 'time'
require 'timeout'
require 'tmpdir'
require 'yaml'

class FactCache
  include Singleton

  MINUTE = 60
  HOUR = 60 * MINUTE
  DAY = 24 * HOUR
  WEEK = 7 * DAY

  def initialize
    @cached_facts_data = nil
    @cache_path = ENV.fetch('FACTER_CACHEPATH',
                            '/var/db/puppet/cached_facts.yaml')
    @cache_disabled = ENV.has_key? 'FACTER_NOCACHE'
    @cache_needs_saving = false

    unless @cache_disabled
      at_exit do
        if @cache_needs_saving
          Facter.debug('Saving Facter cache')
          begin
            lock(@cache_path) do
              File.open(@cache_path, 'w') do |file|
                file.puts @cached_facts_data.to_yaml
              end
            end
          rescue Errno::EPERM, Errno::ACCES => e
            Facter.warn("Error saving fact cache: #{e}")
          end
        end
      end
    end
  end

  def get_fact_with_timeout(factname, expiration, timeout=120, block=Proc.new)
    value = nil
    begin
      tmp_lock = "#{Dir.tmpdir()}/#{factname}"
      lock(tmp_lock, timeout) do
        value = cached_facts_data.fetch(factname, nil)
        unless value.nil?
          if (Time.now - value.fetch('timestamp', 0).to_i).to_i > expiration
            value = nil
          else
            value = value.fetch('value', nil)
          end
        end

        if value.nil?
          value = block.call rescue 'UNKNOWN'
          new_fact = {'value' => value, 'timestamp' => Time.now.to_i}
          cached_facts_data[factname] = new_fact
          @cache_needs_saving = true
        end
      end
    rescue Timeout::Error
      Facter.warn("#{factname} evaluation timed out")
    ensure
      FileUtils.safe_unlink(tmp_lock)
    end
    value
  end

  private

  # Global interprocess lock.
  # If we exceed the timeout, a Timeout::Error is raised.
  def lock(lockname, timeout=0)
    Facter.debug("Locking #{lockname}, timeout #{timeout}")
    File.open(lockname, File::RDWR|File::CREAT, 0644) do |f|
      begin
        Timeout::timeout(timeout) do
          f.flock File::LOCK_EX
          yield
        end
      ensure
        f.flock File::LOCK_UN
      end
    end
    Facter.debug("Unlocking #{lockname}")
  end

  # Remove the cache file if it exists, ensure the directory exists.
  def reset_cache
    Facter.debug('Resetting Facter cache')

    # We just create the directory and let Puppet fix the permissions.
    dir = File::dirname(@cache_path)
    FileUtils::mkdir_p(dir) unless Dir.exists?(dir)

    lock(@cache_path) do
      FileUtils.safe_unlink(@cache_path)
    end

    @cached_facts_data = {}
  end

  def cached_facts_data
    if @cached_facts_data.nil?
      if @cache_disabled
        Facter.debug('Facter cache disabled')
        return @cached_facts_data = {}
      end

      Facter.debug('Loading Facter cache')
      begin
        lock(@cache_path) do
          @cached_facts_data = YAML::load_file(@cache_path)
          @cached_facts_data.each do |k,v|
            unless v.keys.sort() == ['timestamp', 'value']
              Facter.warn("#{k} has invalid value #{v}")
              reset_cache()
              break
            end
          end
        end
      rescue
        Facter.debug('Missing or corrupt cache file')
        reset_cache()
      end
    end
    @cached_facts_data
  end
end

def get_fact_value_with_timeout(factname, expiration, timeout=120,
                                block=Proc.new)
  FactCache.instance.get_fact_with_timeout(factname, expiration, timeout, block)
end

def get_fact_value(factname, expiration, refresh_method, *args)
  get_fact_value_with_timeout(factname, expiration) do
    send(refresh_method, *args)
  end
end
