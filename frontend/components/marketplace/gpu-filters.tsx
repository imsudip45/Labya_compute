"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { Checkbox } from "@/components/ui/checkbox"
import { Search, Filter, X } from "lucide-react"

interface GPUFiltersProps {
  onFiltersChange: (filters: any) => void
  onSearch: (query: string) => void
}

export function GPUFilters({ onFiltersChange, onSearch }: GPUFiltersProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [priceRange, setPriceRange] = useState([0, 10])
  const [memoryRange, setMemoryRange] = useState([0, 80])
  const [selectedLocations, setSelectedLocations] = useState<string[]>([])
  const [selectedModels, setSelectedModels] = useState<string[]>([])
  const [availability, setAvailability] = useState(true)

  const locations = ["New York, USA", "California, USA", "Texas, USA", "Seattle, USA", "Austin, USA", "Florida, USA"]

  const gpuModels = [
    "NVIDIA RTX 4090",
    "NVIDIA RTX 4080 Super",
    "NVIDIA RTX 3080",
    "NVIDIA RTX 3070 Ti",
    "NVIDIA A100",
    "NVIDIA H100",
  ]

  const handleSearch = (query: string) => {
    setSearchQuery(query)
    onSearch(query)
  }

  const handleLocationChange = (location: string, checked: boolean) => {
    const newLocations = checked ? [...selectedLocations, location] : selectedLocations.filter((l) => l !== location)
    setSelectedLocations(newLocations)
    applyFilters({ locations: newLocations })
  }

  const handleModelChange = (model: string, checked: boolean) => {
    const newModels = checked ? [...selectedModels, model] : selectedModels.filter((m) => m !== model)
    setSelectedModels(newModels)
    applyFilters({ models: newModels })
  }

  const applyFilters = (updates: any = {}) => {
    const filters = {
      priceRange,
      memoryRange,
      locations: selectedLocations,
      models: selectedModels,
      availability,
      ...updates,
    }
    onFiltersChange(filters)
  }

  const clearFilters = () => {
    setSearchQuery("")
    setPriceRange([0, 10])
    setMemoryRange([0, 80])
    setSelectedLocations([])
    setSelectedModels([])
    setAvailability(true)
    onSearch("")
    onFiltersChange({
      priceRange: [0, 10],
      memoryRange: [0, 80],
      locations: [],
      models: [],
      availability: true,
    })
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <CardTitle className="flex items-center">
          <Filter className="mr-2 h-5 w-5" />
          Filters
        </CardTitle>
        <Button variant="ghost" size="sm" onClick={clearFilters}>
          <X className="mr-1 h-4 w-4" />
          Clear
        </Button>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Search */}
        <div className="space-y-2">
          <Label>Search GPUs</Label>
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by name or model..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {/* Price Range */}
        <div className="space-y-3">
          <Label>Price Range (Rs./hour)</Label>
          <div className="px-2">
            <Slider
              value={priceRange}
              onValueChange={(value) => {
                setPriceRange(value)
                applyFilters({ priceRange: value })
              }}
              max={1000}
              min={0}
              step={10}
              className="w-full"
            />
          </div>
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>Rs.{priceRange[0]}</span>
            <span>Rs.{priceRange[1]}</span>
          </div>
        </div>

        {/* Memory Range */}
        <div className="space-y-3">
          <Label>Memory (GB VRAM)</Label>
          <div className="px-2">
            <Slider
              value={memoryRange}
              onValueChange={(value) => {
                setMemoryRange(value)
                applyFilters({ memoryRange: value })
              }}
              max={80}
              min={0}
              step={1}
              className="w-full"
            />
          </div>
          <div className="flex justify-between text-sm text-muted-foreground">
            <span>{memoryRange[0]}GB</span>
            <span>{memoryRange[1]}GB</span>
          </div>
        </div>

        {/* Availability */}
        <div className="flex items-center space-x-2">
          <Checkbox
            id="availability"
            checked={availability}
            onCheckedChange={(checked) => {
              setAvailability(checked as boolean)
              applyFilters({ availability: checked })
            }}
          />
          <Label htmlFor="availability">Available only</Label>
        </div>

        {/* GPU Models */}
        <div className="space-y-3">
          <Label>GPU Models</Label>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {gpuModels.map((model) => (
              <div key={model} className="flex items-center space-x-2">
                <Checkbox
                  id={model}
                  checked={selectedModels.includes(model)}
                  onCheckedChange={(checked) => handleModelChange(model, checked as boolean)}
                />
                <Label htmlFor={model} className="text-sm">
                  {model}
                </Label>
              </div>
            ))}
          </div>
        </div>

        {/* Locations */}
        <div className="space-y-3">
          <Label>Locations</Label>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {locations.map((location) => (
              <div key={location} className="flex items-center space-x-2">
                <Checkbox
                  id={location}
                  checked={selectedLocations.includes(location)}
                  onCheckedChange={(checked) => handleLocationChange(location, checked as boolean)}
                />
                <Label htmlFor={location} className="text-sm">
                  {location}
                </Label>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
