# Generate facts based on experiments/canary YAML.

require 'facter'

def get_experiments()
  experiments = {}
  exp_path = '/usr/local/bin/experiments'
  if File.executable?(exp_path)
    Facter.debug("Fetching experiment data with #{exp_path}")
    output = Facter::Util::Resolution.exec("#{exp_path} -F")
    if output
      output.each_line do |line|
        # experiments outputs lines in the format 'exp_name,false'
        match = /^([0-9a-z_]+),(true|false)$/.match(line)
        if match
          experiment = match[1]
          value = match[2]
          Facter.debug("Adding #{experiment} as #{value}")
          experiments["experiment_#{experiment}"] = value
        else
          Facter.warn("Invalid output from #{exp_path}: #{line}")
        end
      end
    end
  else
    Facter.warn("#{exp_path} missing or not executable.")
  end
  experiments
end

get_experiments().each do |experiment,value|
  Facter.add(experiment) do
    setcode do
      value
    end
  end
end
