Write-Host "Powershell script by agauo & modified by ChatGPT"
Write-Host "Credits to patyk73"
1..2 | ForEach-Object { Write-Host "" }

function IsNullOrWhiteSpace($str) {
    [string]::IsNullOrWhiteSpace($str)
}

$global:ProgressPreference = "SilentlyContinue"

function Prompt-UserInput($prompt, $defaultValue = $null, $validate = $null) {
    $inputValue = Read-Host $prompt
    if (-not [string]::IsNullOrWhiteSpace($inputValue) -and $validate -and -not (& $validate $inputValue)) {
        Write-Host "Invalid input! Please try again."
        Prompt-UserInput $prompt $defaultValue $validate
    }
    elseif ([string]::IsNullOrWhiteSpace($inputValue) -and $defaultValue) {
        $inputValue = $defaultValue
    }
    return $inputValue
}

function Download-MsixBundleFile($robloxPath) {
    $productUrl = "https://www.microsoft.com/store/productId/9NBLGGGZM6WM"
    $apiUrl = "https://store.rg-adguard.net/api/GetFiles"

    $body = @{
        type = 'url'
        url  = $productUrl
        ring = 'RP'
        lang = 'en-US'
    }
	
	Write-Host "Necessary msixbundle file not found. Attempting to find link via adguard website: https://store.rg-adguard.net/"
	
    $raw = Invoke-RestMethod -Method Post -Uri $apiUrl -ContentType 'application/x-www-form-urlencoded' -Body $body

    $raw | Select-String '<tr style.*<a href=\"(?<url>.*)"\s.*>(?<text>.*)<\/a>' -AllMatches | ForEach-Object {
        $_.Matches | ForEach-Object {
            $url = $_.Groups[1].Value
            $text = $_.Groups[2].Value

            if ($text -match "_(x86|x64|neutral).*msixbundle$") {
                $downloadFile = Join-Path $robloxPath ($text -replace ".appx(|bundle)$", ".msixbundle")
                if (-not (Test-Path $downloadFile)) {
					Write-Host "Found the link to the Roblox msixbundle file from the adguard website. Attempting to download. This may take a moment."
					$ProgressPreference = 'SilentlyContinue'
                    Invoke-WebRequest -Uri $url -OutFile $downloadFile
                }
            }
        }
    }
	$msixBundle = Get-ChildItem -Path $robloxPath -Filter "*.msixbundle" -File
	if (-not $msixBundle) {
        Write-Host "Error: Failed to download the msixbundle file."
        exit
    } else {
		Write-Host "Download of the msixbundle file completed."
	}
}

$robloxPath = Prompt-UserInput "Enter destination path for the extracted Roblox files (leave blank if you wish to use the current directory)" $PWD.Path

if (-not (Test-Path $robloxPath)) {
    New-Item -Path $robloxPath -ItemType Directory -Force | Out-Null
}

$existingInstances = Get-AppxPackage -PackageTypeFilter Main | Where-Object { $_.PackageFamilyName -like "ROBLOXCORPORATION.ROBLOX.*" }
$existingInstancesCount = $existingInstances.Count

if ($existingInstancesCount -gt 0) {
    Write-Host "The following number of instances already exist: $existingInstancesCount"
    Write-Host "Existing instances: $($existingInstances.Name -join ', ')"
    Write-Host "If you wish to remove these instances, type 'delete' in the following prompt. Otherwise, enter a number."
    $deleteConfirmation = Read-Host "Enter the number of additional cloned instances to create"

    if ($deleteConfirmation -eq "delete") {
        $confirmDelete = Read-Host "Are you sure you want to delete $existingInstancesCount instances? This may take a while and will remove ALL additional instances. (Y/N)"
        if ($confirmDelete -eq "Y") {
            $counter = 1
            foreach ($app in $existingInstances) {
                $appName = "Roblox$counter"
                $counter++
                $packageName = $app.Name
                $packageFullName = $app.PackageFullName
                Write-Host "Uninstalling $packageName"
                Remove-AppxPackage -Package $packageFullName -Confirm:$false
            }

			$deleteFolders = Get-ChildItem -Path $robloxPath -Filter "roblox*" -Directory | Where-Object { $_.Name -match "^roblox\d{1,2}$" }

			if ($deleteFolders.Count -gt 0) {
				foreach ($folder in $deleteFolders) {
					$folderPath = $folder.FullName
					Remove-Item -Path $folderPath -Recurse -Force
					Write-Host "Deleted folder $folderPath"
				}
			}
			else {
				Write-Host "No 'roblox' folders found inside $robloxPath. Skipping deletion."
			}
			$deleteShortcuts = Get-ChildItem -Path $robloxPath -Filter "Roblox*" -File | Where-Object { $_.Name -match "^Roblox\d{1,2}\.lnk$" }

			if ($deleteShortcuts.Count -gt 0) {
				foreach ($shortcut in $deleteShortcuts) {
					$shortcutPath = $shortcut.FullName
					Remove-Item -Path $shortcutPath -Force
					Write-Host "Deleted shortcut file $shortcutPath"
				}
			}
			else {
				Write-Host "No shortcut files found inside $robloxPath. Skipping deletion."
			}
			Write-Host "Uninstallation of all Roblox instances complete."	
			
			$createNewInstances = Read-Host "Do you want to now create new instances? (Y/N)"
			if ($createNewInstances -eq "Y") {
				$clonedInstances = Read-Host "Enter the total number of new instances to create"
				$existingInstances = Get-AppxPackage -PackageTypeFilter Main | Where-Object { $_.PackageFamilyName -like "ROBLOXCORPORATION.ROBLOX.*" }
				$existingInstancesCount = $existingInstances.Count
			} else {
				exit
			}
        }
    }
    else {
        $clonedInstances = [int]$deleteConfirmation
    }
}
else {
    $clonedInstances = Read-Host "Enter the total number of cloned instances to create."
}

$msixfile = Get-ChildItem -Path $robloxPath -Filter "*.msix" -File | Where-Object { $_.Length -gt 100MB } | Sort-Object -Property Length -Descending | Select-Object -First 1
$msixBundle = Get-ChildItem -Path $robloxPath -Filter "*.msixbundle" -File

$templateFolder = Join-Path -Path $robloxPath -ChildPath "template"
$manifestFile = Join-Path -Path $templateFolder -ChildPath "AppxManifest.xml"

if (-not ($msixfile -or $msixBundle -or (Test-Path $templateFolder -PathType Container) -or (Test-Path $manifestFile -PathType Leaf))) {
    Download-MsixBundleFile $robloxPath
}

$templateFolder = Join-Path -Path $robloxPath -ChildPath "template"
$manifestFile = Join-Path -Path $templateFolder -ChildPath "AppxManifest.xml"

if (-not (Test-Path $templateFolder -PathType Container) -or -not (Test-Path $manifestFile -PathType Leaf)) {
    if (-not $msixfile) {
		$msixBundle = Get-ChildItem -Path $robloxPath -Filter "*.msixbundle" -File
        if ($msixBundle) {
            $msixBundlezipFilePath = Join-Path -Path $robloxPath -ChildPath ($msixBundle.BaseName + ".zip")
			Rename-Item -Path $msixBundle.FullName -NewName $msixBundlezipFilePath -Force
			Write-Host "Temporarily renamed .msixbundle file to $msixBundlezipFilePath"

            Write-Host "Extracting the msixbundle file to $robloxPath..."
            Expand-Archive -Path $msixBundlezipFilePath -DestinationPath $robloxPath -Force
			Write-Host "Extraction of msixbundle file completed."

            Rename-Item -Path $msixBundlezipFilePath -NewName $msixbundle.FullName -Force
			Write-Host "Changed the zip file we renamed back to $msixBundle"
			
            $msixfile = Get-ChildItem -Path $robloxPath -Filter "*.msix" -File | Where-Object { $_.Length -gt 100MB } | Sort-Object -Property Length -Descending | Select-Object -First 1
        }
        else {
            Write-Host "Error: No msixbundle file found."
            exit
        }
    }

    Write-Host "Found .msix file $($msixfile)."
    $zipFilePath = Join-Path -Path $robloxPath -ChildPath ($msixfile.BaseName + ".zip")
    Rename-Item -Path $msixfile.FullName -NewName $zipFilePath -Force
	Write-Host "Temporarily renamed .msix file to $zipFilePath"
	
    Write-Host "Extracting msix file to $templateFolder..."
    Expand-Archive -Path $zipFilePath -DestinationPath $templateFolder -Force
	Write-Host "Extraction of msix file completed."

    Rename-Item -Path $zipFilePath -NewName $msixfile.FullName -Force
	Write-Host "Changed the zip file we renamed back to $msixfile"
    $templateFolder = Join-Path -Path $robloxPath -ChildPath "template"
    $manifestFile = Join-Path -Path $templateFolder -ChildPath "AppxManifest.xml"
	
    Write-Host "Extraction of msix file completed."
}

$nextInstanceNumber = $existingInstances.Count + 1

for ($i = $nextInstanceNumber; $i -lt ($nextInstanceNumber + $clonedInstances); $i++) {
    $destinationFolder = Join-Path -Path $robloxPath -ChildPath "roblox$i"
    if ($existingInstances -notcontains "Roblox$i") {
		Write-Host "Creating cloned instance $i in $destinationFolder..."
        Copy-Item -Path $templateFolder -Destination $destinationFolder -Recurse -Force

        $appxSignaturePath = Join-Path -Path $destinationFolder -ChildPath "AppxSignature.p7x"
        if (Test-Path -Path $appxSignaturePath -PathType Leaf) {
			Write-Host "Removing AppxSignature.p7x file in $destinationFolder..."
            Remove-Item -Path $appxSignaturePath -Force
        }

        $appxManifestPath = Join-Path -Path $destinationFolder -ChildPath "AppxManifest.xml"
        if (Test-Path -Path $appxManifestPath -PathType Leaf) {
			Write-Host "Modifying AppxManifest.xml file in $destinationFolder..."
            (Get-Content -Path $appxManifestPath) `
                -replace '<Identity Name="ROBLOXCORPORATION.ROBLOX"', "<Identity Name=`"ROBLOXCORPORATION.ROBLOX.$i`"" `
                -replace '<DisplayName>Roblox</DisplayName>', "<DisplayName>Roblox$i</DisplayName>" `
                -replace '<uap:VisualElements DisplayName="Roblox"', "<uap:VisualElements DisplayName=`"Roblox$i`"" `
                -replace '<uap:DefaultTile ShortName="Roblox"', "<uap:DefaultTile ShortName=`"Roblox$i`"" `
                -replace '<uap:Protocol Name="roblox"', "<uap:Protocol Name=`"roblox-uwp$i`"" `
            | Set-Content -Path $appxManifestPath
        }
    }
	Write-Host "Installing cloned instance $i..."
    Add-AppxPackage -Path $appxManifestPath -Register
}

$apps = Get-AppxPackage -PackageTypeFilter Main | Where-Object { $_.PackageFamilyName -like "ROBLOXCORPORATION.ROBLOX.*" }
$wshShell = New-Object -ComObject WScript.Shell
$counter = 1

foreach ($app in $apps) {
    $appName = "Roblox$counter"
    $counter++
    $packageFamilyName = $app.PackageFamilyName
    $appPath = "shell:AppsFolder\$packageFamilyName!App"
    $shortcutName = "$appName.lnk"
    $shortcutPath = Join-Path -Path $robloxPath -ChildPath $shortcutName

    if (-not (Test-Path $shortcutPath)) {
        $shortcut = $wshShell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $appPath
        $shortcut.Save()

        Write-Host "Shortcut created for $appName $shortcutPath"
    }
}

# --- NEW CLIENTAPPSETTINGS HANDLING ---
$clientSettingsPath = Join-Path -Path $robloxPath -ChildPath "clientappsettings.json"
$currentUserAppData = [System.Environment]::GetFolderPath("LocalApplicationData")

if (Test-Path -Path $clientSettingsPath -PathType Leaf) {
    Write-Host "Template clientappsettings.json found."

    foreach ($app in (Get-AppxPackage -PackageTypeFilter Main | Where-Object { $_.PackageFamilyName -like "ROBLOXCORPORATION.ROBLOX.*" })) {
        $instanceNumber = [regex]::Match($app.PackageFamilyName, "\d+").Value
        $robloxFolder = Get-ChildItem -Path "$currentUserAppData\Packages" -Filter "ROBLOXCORPORATION.ROBLOX.$instanceNumber*" -Directory | Select-Object -First 1
        
        if ($robloxFolder -ne $null) {
            $settingsDest = Join-Path -Path $robloxFolder.FullName -ChildPath "LocalState\ClientSettings"
            if (-not (Test-Path $settingsDest)) {
                New-Item -Path $settingsDest -ItemType Directory -Force | Out-Null
            }
            Copy-Item -Path $clientSettingsPath -Destination $settingsDest -Force
            Write-Host "Copied clientappsettings.json to $settingsDest"
        }
    }
} else {
    Write-Host "No clientappsettings.json found in $robloxPath"
}

Write-Host "Installation complete. You can close this window. Shortcuts are located in $robloxPath"
exit
