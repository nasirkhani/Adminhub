param (
    # The length of each password which should be created.
    [Parameter(Mandatory = $true)]
    [ValidateRange(8, 255)]
    [Int32]$Length,

    # The number of passwords to generate.
    [Parameter(Mandatory = $false)]
    [Int32]$Count = 1,

    # The character sets the password may contain.
    # A password will contain at least one of each of the characters.
    [ValidateScript({
        if ($_.Count -eq 0) {
            throw "CharacterSet must contain at least one set."
        }
        foreach ($set in $_) {
            if ($set.Length -eq 0) {
                throw "Each character set in CharacterSet must be non-empty."
            }
        }
        $true
    })]
    [String[]]$CharacterSet = @(
        'abcdefghijklmnopqrstuvwxyz',
        'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        '0123456789',
        '!$%&^.#;'
    ),

    # Conversion options
    [Parameter(Mandatory = $false)]
    [ValidateSet("Binary", "Hexadecimal", "Decimal", "Octal", "Text", "All")]
    [String]$ConvertTo = "Text"
)

# Validate that Length is at least the number of character sets
if ($Length -lt $CharacterSet.Count) {
    throw "Length must be at least the number of character sets ($($CharacterSet.Count))."
}

# Create a cryptographically secure RNG
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()

# Function to convert a string to binary
function Convert-ToBinary {
    param ([String]$InputString)
    $binary = $InputString.ToCharArray() | ForEach-Object {
        [System.Convert]::ToString([int][char]$_, 2).PadLeft(8, '0')
    }
    return $binary -join ' '
}

# Function to convert a string to hexadecimal
function Convert-ToHex {
    param ([String]$InputString)
    $hex = $InputString.ToCharArray() | ForEach-Object {
        [System.Convert]::ToString([int][char]$_, 16).PadLeft(2, '0')
    }
    return $hex -join ' '
}

# Function to convert a string to decimal
function Convert-ToDecimal {
    param ([String]$InputString)
    $decimal = $InputString.ToCharArray() | ForEach-Object {
        [int][char]$_
    }
    return $decimal -join ' '
}

# Function to convert a string to octal
function Convert-ToOctal {
    param ([String]$InputString)
    $octal = $InputString.ToCharArray() | ForEach-Object {
        [System.Convert]::ToString([int][char]$_, 8).PadLeft(3, '0')
    }
    return $octal -join ' '
}

# Function to display all conversions
function Show-AllConversions {
    param ([String]$InputString)
    Write-Host "Text: $InputString"
    Write-Host "Binary: $(Convert-ToBinary $InputString)"
    Write-Host "Hexadecimal: $(Convert-ToHex $InputString)"
    Write-Host "Decimal: $(Convert-ToDecimal $InputString)"
    Write-Host "Octal: $(Convert-ToOctal $InputString)"
}

try {
    $allCharacterSets = [String]::Concat($CharacterSet)
    $charSetCount = $CharacterSet.Count

    for ($i = 0; $i -lt $Count; $i++) {
        $password = [Char[]]::new($Length)
        $index = 0

        # Ensure at least one character from each set
        foreach ($set in $CharacterSet) {
            $setLength = $set.Length
            $bytes = [Byte[]]::new(4)
            $rng.GetBytes($bytes)
            $randomIndex = [BitConverter]::ToUInt32($bytes, 0) % $setLength
            $password[$index++] = $set[$randomIndex]
        }

        # Fill remaining characters from all combined sets
        $remaining = $Length - $charSetCount
        if ($remaining -gt 0) {
            $totalChars = $allCharacterSets.Length
            for ($j = 0; $j -lt $remaining; $j++) {
                $bytes = [Byte[]]::new(4)
                $rng.GetBytes($bytes)
                $randomIndex = [BitConverter]::ToUInt32($bytes, 0) % $totalChars
                $password[$index++] = $allCharacterSets[$randomIndex]
            }
        }

        # Fisher-Yates shuffle using cryptographic RNG
        for ($j = $Length - 1; $j -ge 1; $j--) {
            $bytes = [Byte[]]::new(4)
            $rng.GetBytes($bytes)
            $k = [BitConverter]::ToUInt32($bytes, 0) % ($j + 1)
            $temp = $password[$j]
            $password[$j] = $password[$k]
            $password[$k] = $temp
        }

        $passwordString = [String]::new($password)

        # Display conversions based on user input
        switch ($ConvertTo) {
            "Binary" {
                Write-Host "Binary: $(Convert-ToBinary $passwordString)"
            }
            "Hexadecimal" {
                Write-Host "Hexadecimal: $(Convert-ToHex $passwordString)"
            }
            "Decimal" {
                Write-Host "Decimal: $(Convert-ToDecimal $passwordString)"
            }
            "Octal" {
                Write-Host "Octal: $(Convert-ToOctal $passwordString)"
            }
            "Text" {
                Write-Host "Text: $passwordString"
            }
            "All" {
                Show-AllConversions $passwordString
            }
        }
    }
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
finally {
    $rng.Dispose()
}