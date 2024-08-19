import os

def generate_env_example(input_file=".env", output_file=".env.example"):
    try:
        with open(input_file, "r") as infile, open(output_file, "w") as outfile:
            for line in infile:
                # Skip lines that start with USER or SINCH
                if line.startswith("USER") or line.startswith("SINCH"):
                    continue
                
                # Write the sanitized line to the output file
                key, _, _ = line.partition("=")
                outfile.write(f"{key}=\n")
        
        print(f"{output_file} has been generated successfully.")
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")

if __name__ == "__main__":
    generate_env_example()