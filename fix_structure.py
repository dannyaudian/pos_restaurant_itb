import os
import shutil
import sys

# Function to create directory if it doesn't exist
def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")

# Create base directories
clean_dir = os.path.expanduser("~/clean_pos")
ensure_dir(clean_dir)
ensure_dir(os.path.join(clean_dir, "pos_restaurant_itb"))
ensure_dir(os.path.join(clean_dir, "pos_restaurant_itb", "doctype"))

# Current working directory
current_dir = os.getcwd()
print(f"Current directory: {current_dir}")

# Find all doctype directories
doctype_paths = []
for root, dirs, files in os.walk(current_dir):
    if "doctype" in dirs:
        doctype_path = os.path.join(root, "doctype")
        doctype_paths.append(doctype_path)

if not doctype_paths:
    print("Error: No doctype directories found!")
    sys.exit(1)

# Sort by path length (descending) to find the deepest directory
doctype_paths.sort(key=len, reverse=True)
main_doctype_path = doctype_paths[0]
print(f"Using doctype directory: {main_doctype_path}")

# Copy DocTypes
for doctype_name in os.listdir(main_doctype_path):
    source_doctype_path = os.path.join(main_doctype_path, doctype_name)
    if os.path.isdir(source_doctype_path):
        target_doctype_path = os.path.join(clean_dir, "pos_restaurant_itb", "doctype", doctype_name)
        ensure_dir(target_doctype_path)
        
        # Copy files in the doctype directory
        for filename in os.listdir(source_doctype_path):
            source_file = os.path.join(source_doctype_path, filename)
            target_file = os.path.join(target_doctype_path, filename)
            if os.path.isfile(source_file):
                shutil.copy2(source_file, target_file)
                print(f"Copied {filename} to {target_doctype_path}")
        
        # Create __init__.py if it doesn't exist
        init_py = os.path.join(target_doctype_path, "__init__.py")
        if not os.path.exists(init_py):
            with open(init_py, 'w') as f:
                f.write("# Auto-generated __init__.py\n")
            print(f"Created {init_py}")

# Find and copy hooks.py
hooks_files = []
for root, dirs, files in os.walk(current_dir):
    if "hooks.py" in files:
        hooks_path = os.path.join(root, "hooks.py")
        hooks_files.append(hooks_path)

if hooks_files:
    hooks_files.sort(key=len)  # Sort by path length (ascending)
    hooks_path = hooks_files[0]
    target_hooks = os.path.join(clean_dir, "pos_restaurant_itb", "hooks.py")
    shutil.copy2(hooks_path, target_hooks)
    print(f"Copied hooks.py from {hooks_path} to {target_hooks}")
else:
    print("Warning: hooks.py not found!")

# Find and copy __init__.py
init_files = []
for root, dirs, files in os.walk(current_dir):
    if "__init__.py" in files and "pos_restaurant_itb" in root:
        init_path = os.path.join(root, "__init__.py")
        init_files.append(init_path)

if init_files:
    init_files.sort(key=len)  # Sort by path length
    init_path = init_files[0]
    target_init = os.path.join(clean_dir, "pos_restaurant_itb", "__init__.py")
    shutil.copy2(init_path, target_init)
    print(f"Copied __init__.py from {init_path} to {target_init}")
else:
    target_init = os.path.join(clean_dir, "pos_restaurant_itb", "__init__.py")
    with open(target_init, 'w') as f:
        f.write("# Auto-generated __init__.py\n")
    print(f"Created {target_init}")

# Function to copy directory and contents
def copy_directory(dir_name):
    dir_paths = []
    for root, dirs, files in os.walk(current_dir):
        if dir_name in dirs and "pos_restaurant_itb" in root:
            dir_path = os.path.join(root, dir_name)
            dir_paths.append(dir_path)
    
    if dir_paths:
        dir_paths.sort(key=len, reverse=True)  # Get deepest path
        source_dir = dir_paths[0]
        target_dir = os.path.join(clean_dir, "pos_restaurant_itb", dir_name)
        ensure_dir(target_dir)
        
        # Create __init__.py
        init_py = os.path.join(target_dir, "__init__.py")
        if not os.path.exists(init_py):
            with open(init_py, 'w') as f:
                f.write("# Auto-generated __init__.py\n")
        
        # Copy files
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                source_file = os.path.join(root, file)
                # Get relative path from source_dir
                rel_path = os.path.relpath(source_file, source_dir)
                target_file = os.path.join(target_dir, rel_path)
                # Create subdirectories if needed
                ensure_dir(os.path.dirname(target_file))
                # Copy file
                shutil.copy2(source_file, target_file)
                print(f"Copied {rel_path} to {target_dir}")
        
        return True
    return False

# Copy important directories
for directory in ["api", "utils", "public", "templates", "config"]:
    if copy_directory(directory):
        print(f"Copied {directory} directory")
    else:
        print(f"Warning: {directory} directory not found")

# Copy root files
root_files = ["README.md", "LICENSE", "MANIFEST.in", "setup.py", "requirements.txt", "modules.txt"]
for file in root_files:
    file_paths = []
    for root, dirs, files in os.walk(current_dir):
        if file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)
    
    if file_paths:
        file_paths.sort(key=len)  # Sort by path length
        source_file = file_paths[0]
        target_file = os.path.join(clean_dir, file)
        shutil.copy2(source_file, target_file)
        print(f"Copied {file} from {source_file} to {target_file}")
    else:
        print(f"Warning: {file} not found")

print("\nDirectory structure fixed. Files copied to:", clean_dir)
print("\nNext steps:")
print("1. Check the new structure: find ~/clean_pos -type f | sort")
print("2. Go to clean_pos directory: cd ~/clean_pos")
print("3. Initialize git: git init")
print("4. Add files: git add .")
print("5. Commit: git commit -m \"Fix directory structure\"")
print("6. Add remote: git remote add origin https://github.com/dannyaudian/Restaurant-Management.git")
print("7. Create branch: git checkout -b fixed-structure")
print("8. Push: git push -u origin fixed-structure")
print("9. Create a pull request on GitHub")